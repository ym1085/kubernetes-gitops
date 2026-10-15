import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/gitops"))
import validate


class ChartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = validate.read_yaml(ROOT / "argocd/applications/dev/apps/farm-market-api.yaml")
        cls.project = validate.read_yaml(ROOT / "argocd/projects/dev/apps/farm-market.yaml")
        cls.resources = validate.render(cls.app, fixtures=True)

    def test_api_profiles_ports_without_runtime_secret(self):
        for environment, profile, port in (("dev", "dev", 8081), ("stg", "dev", 8081), ("prod", "prod", 8082)):
            with self.subTest(environment=environment):
                app = validate.read_yaml(ROOT / f"argocd/applications/{environment}/apps/farm-market-api.yaml")
                resources = validate.render(app, fixtures=True)
                pod = next(r for r in resources if r["kind"] == "Deployment")["spec"]["template"]["spec"]
                container = pod["containers"][0]
                env = {e["name"]: e for e in container["env"]}
                self.assertEqual(env["SPRING_PROFILES_ACTIVE"]["value"], profile)
                self.assertEqual(env["FARMMARKET_IMAGE_STORAGELOCATION"]["value"], "file:/data/uploads/")
                self.assertEqual(container["ports"][0]["containerPort"], port)
                self.assertGreater(pod["terminationGracePeriodSeconds"], 60 if profile == "prod" else 30)
                self.assertTrue(all("valueFrom" not in entry for entry in container["env"]))
                self.assertNotIn("JWT_SECRET", env)
                self.assertNotIn("SPRING_DATASOURCE_PASSWORD", env)

    def test_env_survives_resource_removal_and_preserves_empty_values(self):
        extra_env = [
            {"name": "EMPTY", "value": ""},
            {"name": "FEATURE_ENABLED", "value": "false"},
            {"name": "RETRY_COUNT", "value": "0"},
            {"name": "REDIS_HOST", "value": "redis.example"},
        ]
        resources = validate.render(self.app, fixtures=True, extra=[
            "--set-json", "resources={\"requests\":null,\"limits\":null}",
            "--set-json", "env=" + json.dumps(extra_env),
        ])
        container = next(r for r in resources if r["kind"] == "Deployment")["spec"]["template"]["spec"]["containers"][0]
        env = {e["name"]: e for e in container["env"]}
        self.assertEqual(container["resources"], {})
        self.assertEqual(container["env"][2:], extra_env)
        self.assertNotIn("FARMMARKET_IMAGE_STORAGELOCATION", env)
        self.assertNotIn("JWT_SECRET", env)
        validate.validate_resources(self.app, self.project, resources, "traefik-dev")

    def test_empty_env_list_keeps_generated_variables(self):
        resources = validate.render(self.app, fixtures=True, extra=["--set-json", "env=[]"])
        container = next(r for r in resources if r["kind"] == "Deployment")["spec"]["template"]["spec"]["containers"][0]
        self.assertEqual(container["env"], [
            {"name": "SPRING_PROFILES_ACTIVE", "value": "dev"},
            {"name": "SERVER_PORT", "value": "8081"},
        ])

    def test_validator_rejects_duplicate_env_names(self):
        for second_value in ("first", "second"):
            with self.subTest(second_value=second_value):
                env = [{"name": "DUPLICATE", "value": "first"}, {"name": "DUPLICATE", "value": second_value}]
                resources = validate.render(self.app, fixtures=True, extra=["--set-json", "env=" + json.dumps(env)])
                with self.assertRaisesRegex(ValueError, "Duplicate container environment variable"):
                    validate.validate_resources(self.app, self.project, resources, "traefik-dev")

    def test_env_rejects_invalid_entries(self):
        invalid = [
            {"LEGACY_MAP": "value"},
            [{"name": "MISSING_VALUE"}],
            [{"value": "missing name"}],
            [{"name": "INVALID-NAME", "value": "value"}],
            [{"name": "FEATURE_ENABLED", "value": False}],
            [{"name": "RETRY_COUNT", "value": 0}],
            [{"name": "EMPTY", "value": None}],
            [{"name": "UNSUPPORTED", "value": "value", "unknown": "field"}],
        ]
        invalid += [[{"name": name, "value": "override"}] for name in (
            "SERVER_PORT", "SPRING_PROFILES_ACTIVE", "SPRING_DATASOURCE_PASSWORD", "JWT_SECRET", "REDIS_PASSWORD",
        )]
        for env in invalid:
            with self.subTest(env=env), self.assertRaises(ValueError):
                validate.render(self.app, fixtures=True, extra=["--set-json", "env=" + json.dumps(env)])

    def test_release_name_is_used_for_all_connections(self):
        app = copy.deepcopy(self.app)
        app["spec"]["source"]["helm"]["releaseName"] = "another-release"
        resources = validate.render(app, fixtures=True)
        validate.validate_resources(app, self.project, resources, "traefik-dev")
        self.assertEqual({r["metadata"]["name"] for r in resources}, {"another-release"})

    def test_invalid_values_fail_before_deployment(self):
        invalid = [
            ["--set-string", "image.repository="],
            ["--set-string", "image.tag=latest"],
            ["--set", "containerPort=0"],
            ["--set-string", "existingSecret="],
            ["--set-string", "springProfile=stg"],
            ["--set-string", "springProfile=prod", "--set", "terminationGracePeriodSeconds=30"],
        ]
        for arguments in invalid:
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                validate.render(self.app, fixtures=True, extra=arguments)

    def test_validator_rejects_broken_connections(self):
        for failure in ("namespace", "selector", "targetPort", "ingress", "class"):
            with self.subTest(failure=failure):
                resources = copy.deepcopy(self.resources)
                service = next(r for r in resources if r["kind"] == "Service")
                ingress = next(r for r in resources if r["kind"] == "Ingress")
                if failure == "namespace":
                    service["metadata"]["namespace"] = "wrong-environment"
                elif failure == "selector":
                    service["spec"]["selector"]["app.kubernetes.io/instance"] = "missing"
                elif failure == "targetPort":
                    service["spec"]["ports"][0]["targetPort"] = "missing"
                elif failure == "ingress":
                    ingress["spec"]["rules"][0]["http"]["paths"][0]["backend"]["service"]["name"] = "missing"
                else:
                    ingress["spec"]["ingressClassName"] = "traefik-prod"
                with self.assertRaises(ValueError):
                    validate.validate_resources(self.app, self.project, resources, "traefik-dev")


class PolicyTests(unittest.TestCase):
    def test_bootstrap_rejects_missing_namespace_and_insecure_admin_access(self):
        for environment in ("dev", "stg", "prod"):
            apps = {p.stem: validate.read_yaml(p) for p in (ROOT / "argocd/applications" / environment).rglob("*.yaml")}
            validate.validate_bootstrap(environment, apps)
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                shutil.copytree(ROOT / "argocd/bootstrap", root / "argocd/bootstrap")
                namespaces = root / f"argocd/bootstrap/{environment}/namespaces.yaml"
                namespaces.write_text(f"apiVersion: v1\nkind: Namespace\nmetadata:\n  name: farm-market-{environment}\n")
                with patch.object(validate, "ROOT", root), self.assertRaisesRegex(ValueError, "Bootstrap namespaces"):
                    validate.validate_bootstrap(environment, apps)
                shutil.copyfile(ROOT / f"argocd/bootstrap/{environment}/namespaces.yaml", namespaces)
                override = root / f"argocd/bootstrap/{environment}/argo-cd-install-values.yaml"
                original = override.read_text()
                override.write_text(original + "\nconfigs:\n  params:\n    server.insecure: true\n")
                with patch.object(validate, "ROOT", root), self.assertRaisesRegex(ValueError, "TLS"):
                    validate.validate_bootstrap(environment, apps)
                if environment == "prod":
                    override.write_text(original.replace("type: ClusterIP", "type: NodePort"))
                    with patch.object(validate, "ROOT", root), self.assertRaisesRegex(ValueError, "external Service"):
                        validate.validate_bootstrap(environment, apps)

    def test_prod_rejects_implicit_and_explicit_auto_sync(self):
        validate.validate_sync_policy({"syncPolicy": {}}, "prod")
        for automated in ({}, {"enabled": True}, {"enabled": None}, {"prune": True, "selfHeal": True}):
            with self.subTest(automated=automated), self.assertRaises(ValueError):
                validate.validate_sync_policy({"syncPolicy": {"automated": automated}}, "prod")
        for environment in ("dev", "stg"):
            validate.validate_sync_policy({"syncPolicy": {"automated": {"prune": True, "selfHeal": True}}}, environment)
            with self.assertRaises(ValueError):
                validate.validate_sync_policy({"syncPolicy": {}}, environment)

    def test_cluster_permissions_only_allow_controller_kinds(self):
        for environment in ("dev", "stg", "prod"):
            app = validate.read_yaml(ROOT / f"argocd/applications/{environment}/infra/traefik.yaml")
            project = validate.read_yaml(ROOT / f"argocd/projects/{environment}/infra/project.yaml")
            for kind, version in (("ClusterRole", "rbac.authorization.k8s.io/v1"), ("ClusterRoleBinding", "rbac.authorization.k8s.io/v1"), ("IngressClass", "networking.k8s.io/v1")):
                resource = {"apiVersion": version, "kind": kind, "metadata": {"name": "controller"}}
                validate.validate_resources(app, project, [resource], f"traefik-{environment}")
                restricted = copy.deepcopy(project)
                restricted["spec"]["clusterResourceWhitelist"] = []
                with self.assertRaises(ValueError):
                    validate.validate_resources(app, restricted, [resource], f"traefik-{environment}")
            for kind, version in (("Namespace", "v1"), ("CustomResourceDefinition", "apiextensions.k8s.io/v1")):
                self.assertFalse(validate.allowed({"kind": kind, "apiVersion": version}, project["spec"]["clusterResourceWhitelist"]))


class SetupScriptTests(unittest.TestCase):
    def test_namespaces_are_prepared_before_roots_and_failure_stops_registration(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            log = directory / "calls"
            kubectl = directory / "kubectl"
            kubectl.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$KUBECTL_TEST_LOG"\nif [[ "$1" == get && "${MISSING_PROJECT:-0}" == 1 ]]; then exit 1; fi\nif [[ "$*" == *namespaces.yaml && "${FAIL_NAMESPACES:-0}" == 1 ]]; then exit 1; fi\n')
            kubectl.chmod(0o755)
            env = {**os.environ, "PATH": f"{directory}:{os.environ['PATH']}", "KUBECTL_TEST_LOG": str(log)}
            scripts = ROOT / "scripts/gitops/argocd"
            for environment in ("dev", "stg", "prod"):
                for script in ("setup-appprojects.sh", "setup-applications.sh"):
                    log.write_text("")
                    result = subprocess.run(["bash", str(scripts / script), environment], env=env, text=True, capture_output=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    applied = [line.split()[-1] for line in log.read_text().splitlines() if line.startswith("apply ")]
                    expected = ["namespaces.yaml", "root-project.yaml", "projects-root.yaml"] if script == "setup-appprojects.sh" else ["namespaces.yaml", "applications-root.yaml"]
                    self.assertEqual(applied, [str(ROOT / f"argocd/bootstrap/{environment}/{name}") for name in expected])
                    log.write_text("")
                    result = subprocess.run(["bash", str(scripts / script), environment], env={**env, "FAIL_NAMESPACES": "1"}, text=True, capture_output=True)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn("-root.yaml", log.read_text())
                    self.assertNotIn("root-project.yaml", log.read_text())
            log.write_text("")
            for script in ("setup-appprojects.sh", "setup-applications.sh"):
                result = subprocess.run(["bash", str(scripts / script), "invalid"], env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 2)
            self.assertEqual(log.read_text(), "")
            result = subprocess.run(["bash", str(scripts / "setup-applications.sh"), "dev"], env={**env, "MISSING_PROJECT": "1"}, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("apply", log.read_text())


if __name__ == "__main__":
    unittest.main()
