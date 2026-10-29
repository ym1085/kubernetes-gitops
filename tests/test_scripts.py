import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ARGOCD = "gitops/argocd/install-argocd.sh"
OIDC = "aws/eks/associate-iam-oidc-provider.sh"
CONTROLLER = "aws/eks/aws-load-balancer-controller/"


class ScriptTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.work = Path(directory.name)
        self.log = self.work / "calls"
        stub = '''#!/bin/bash
command="${0##*/} $*"
printf '%s\\n' "$command" >> "$SCRIPT_TEST_LOG"
if [[ -n "${FAIL_COMMAND:-}" && "$command" == "$FAIL_COMMAND"* ]]; then
    echo "Simulated command failure" >&2
    exit 42
fi
if [[ "$command" == "kind create cluster "* ]]; then
    [[ "$#" == 4 && "$3" == --config && -f "$4" ]] || exit 43
fi
if [[ "$command" == "kubectl get namespace argocd" ]]; then
    exit "$NAMESPACE_EXIT"
fi
if [[ "$command" == "kubectl -n argocd get secret "* ]]; then
    printf '%s' "$PASSWORD_BASE64"
fi
'''
        for name in ("aws", "eksctl", "helm", "kubectl", "curl", "sleep", "kind"):
            path = self.work / name
            path.write_text(stub)
            path.chmod(0o755)
        self.env = {
            **os.environ,
            "PATH": f"{self.work}:{os.environ['PATH']}",
            "TMPDIR": str(self.work),
            "SCRIPT_TEST_LOG": str(self.log),
            "FAIL_COMMAND": "",
            "NAMESPACE_EXIT": "1",
            "PASSWORD_BASE64": "dGVzdC1wYXNzd29yZA==",
            "CLUSTER_NAME": "test-cluster",
            "ACCOUNT_ID": "123456789012",
            "DEFAULT_REGION": "ap-northeast-2",
            "REGION": "us-east-1",
            "VPC_ID": "vpc-test",
        }

    def run_script(self, script, **overrides):
        self.log.write_text("")
        result = subprocess.run(
            ["bash", str(ROOT / "scripts" / script)],
            cwd=self.work, env={**self.env, **overrides}, input="1\n",
            text=True, capture_output=True, timeout=10,
        )
        return result, self.log.read_text().splitlines()

    def test_policy_failure_stops_and_cleans_up_download(self):
        existing = self.work / "alb-controller-iam-policy.json"
        existing.write_text("existing policy")
        for failed_command in ("curl", "aws iam create-policy"):
            with self.subTest(failed_command=failed_command):
                result, calls = self.run_script(
                    CONTROLLER + "create-iam-policy.sh", FAIL_COMMAND=failed_command,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(calls[-1].startswith(failed_command), calls)
                download = shlex.split(calls[0])
                self.assertIn("-fsSL", download)
                self.assertFalse(Path(download[download.index("-o") + 1]).exists())
                self.assertEqual(existing.read_text(), "existing policy")

    def test_kind_uses_named_config_and_context_and_stops_on_failure(self):
        directory = self.work / "kind scripts"
        shutil.copytree(ROOT / "scripts/k8s/kind-cluster", directory)
        (directory / "another-config.yaml").write_text("invalid config")
        create = directory / "create-cluster.sh"
        result, calls = self.run_script(create)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, [
            f"kind create cluster --config {directory}/nodeport-config.yaml",
            "kubectl --context kind-helm-cluster get nodes",
        ])
        result, calls = self.run_script(create, FAIL_COMMAND="kind create")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(calls), 1)
        result, calls = self.run_script(directory / "delete-cluster.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, ["kind delete cluster --name helm-cluster"])

    def test_controller_stops_at_failed_command(self):
        for failed_command in (
            "helm repo add", "helm repo update", "helm upgrade",
            "kubectl -n kube-system rollout", "kubectl -n kube-system logs",
        ):
            with self.subTest(failed_command=failed_command):
                result, calls = self.run_script(
                    CONTROLLER + "deploy-controller.sh", FAIL_COMMAND=failed_command,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(calls[-1].startswith(failed_command), calls)

    def test_eksctl_scripts_use_same_region_and_report_failures(self):
        for script in (OIDC, CONTROLLER + "create-iam-service-account.sh"):
            with self.subTest(script=script):
                result, calls = self.run_script(script)
                self.assertEqual(result.returncode, 0, result.stderr)
                arguments = shlex.split(calls[0])
                self.assertEqual(arguments[arguments.index("--region") + 1], "ap-northeast-2")
                result, _ = self.run_script(script, FAIL_COMMAND="eksctl")
                self.assertNotEqual(result.returncode, 0)

    def test_missing_aws_inputs_fail_before_any_command(self):
        for script, variables in (
            (OIDC, ("CLUSTER_NAME", "DEFAULT_REGION")),
            (CONTROLLER + "create-iam-service-account.sh", ("CLUSTER_NAME", "DEFAULT_REGION", "ACCOUNT_ID")),
            (CONTROLLER + "deploy-controller.sh", ("CLUSTER_NAME", "DEFAULT_REGION", "VPC_ID")),
        ):
            for variable in variables:
                with self.subTest(script=script, variable=variable):
                    result, calls = self.run_script(script, **{variable: ""})
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(variable, result.stderr)
                    self.assertEqual(calls, [])

    def test_existing_argocd_namespace_still_stops_installation(self):
        result, calls = self.run_script(ARGOCD, NAMESPACE_EXIT="0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already exists", result.stdout)
        self.assertEqual(calls, ["kubectl get namespace argocd"])

    def test_argocd_password_failure_never_reports_success(self):
        for overrides in (
            {"FAIL_COMMAND": "kubectl -n argocd get secret"},
            {"PASSWORD_BASE64": ""},
            {"PASSWORD_BASE64": "invalid-base64!"},
            {"PASSWORD_BASE64": "dGVzdA"},
            {"PASSWORD_BASE64": "dGVzdA==!"},
            {"PASSWORD_BASE64": "=dGVzdA="},
        ):
            with self.subTest(overrides=overrides):
                result, _ = self.run_script(ARGOCD, **overrides)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("ArgoCD 설치가 완료되었습니다.", result.stdout)
                self.assertNotIn("ArgoCD Password:", result.stdout)

    def test_successful_installation_and_policy_creation(self):
        for script in (ARGOCD, CONTROLLER + "create-iam-policy.sh", CONTROLLER + "deploy-controller.sh"):
            with self.subTest(script=script):
                result, calls = self.run_script(script)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(calls)
                if script == ARGOCD:
                    self.assertIn("ArgoCD Password: test-password", result.stdout)
                    arguments = shlex.split(next(call for call in calls if call.startswith("helm install ")))
                    values = [Path(arguments[i + 1]).resolve() for i, arg in enumerate(arguments) if arg == "-f"]
                    self.assertEqual(values, [
                        ROOT / "argocd/bootstrap/common/argo-cd-install-values.yaml",
                        ROOT / "argocd/bootstrap/dev/install/argo-cd-install-values.yaml",
                    ])
                    self.assertTrue(all(path.is_file() for path in values))


if __name__ == "__main__":
    unittest.main()
