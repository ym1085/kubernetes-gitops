#!/usr/bin/env python3
"""Validate Argo CD declarations and render local and optionally external Helm charts."""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[2]
HELM = os.environ.get("HELM", "helm")
REVISIONS = {"dev": "dev", "stg": "stg", "prod": "master"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_yaml(path):
    with path.open() as stream:
        return yaml.safe_load(stream)


def declaration_paths(directory):
    return sorted(
        path for path in directory.rglob("*")
        if path.is_file() and path.suffix in {".yaml", ".yml", ".json"}
    )


def run_helm(arguments):
    result = subprocess.run([HELM, *arguments], text=True, capture_output=True, timeout=60)
    require(result.returncode == 0, result.stdout + result.stderr)
    return result.stdout


def chart_arguments(app, fixtures=False):
    source = app["spec"]["source"]
    chart = ROOT / source["path"]
    require(chart.is_dir(), f"Missing chart: {chart}")
    helm = source["helm"]
    require(set(helm) <= {"releaseName", "valueFiles"}, "Use valueFiles for local chart configuration")
    arguments = []
    image = read_yaml(chart / "values.yaml").get("image", {}).copy()
    for name in helm["valueFiles"]:
        path = chart / name
        require(path.is_file(), f"Missing values file: {path}")
        arguments += ["-f", str(path)]
        image.update((read_yaml(path) or {}).get("image", {}))
    if fixtures:
        for key, value in {"repository": "registry.invalid/farm-market-api", "tag": "ci-test"}.items():
            if not image.get(key):
                arguments += ["--set-string", f"image.{key}={value}"]
    return str(chart), arguments


def render(app, fixtures=False, extra=()):
    chart, arguments = chart_arguments(app, fixtures)
    release = app["spec"]["source"]["helm"].get("releaseName", app["metadata"]["name"])
    output = run_helm([
        "template", release, chart, "--namespace", app["spec"]["destination"]["namespace"],
        "--kube-version", "1.35.1", *arguments, *extra,
    ])
    return [doc for doc in yaml.safe_load_all(output) if doc]


def allowed(resource, entries):
    group = resource["apiVersion"].split("/")[0] if "/" in resource["apiVersion"] else ""
    return any(entry["group"] in (group, "*") and entry["kind"] in (resource["kind"], "*") for entry in entries)


def validate_sync_policy(spec, environment):
    automated = spec["syncPolicy"].get("automated")
    # Argo CD enables auto-sync for {}, so prod must omit the policy entirely.
    require(automated is None if environment == "prod" else automated == {"prune": True, "selfHeal": True},
            f"Wrong {environment} workload sync policy")


def validate_bootstrap(environment, apps):
    bootstrap = ROOT / "argocd/bootstrap" / environment
    namespaces = [
        namespace
        for path in sorted((bootstrap / "namespaces").iterdir())
        if path.is_file() and path.suffix in {".yaml", ".yml", ".json"}
        for namespace in yaml.safe_load_all(path.read_text())
    ]
    require(all(ns and ns.get("apiVersion") == "v1" and ns.get("kind") == "Namespace" for ns in namespaces),
            f"Bootstrap must contain only Namespace resources: {environment}")
    names = [ns["metadata"]["name"] for ns in namespaces]
    expected = {app["spec"]["destination"]["namespace"] for app in apps.values()} - {"argocd"}
    require(len(names) == len(set(names)) and set(names) == expected, f"Bootstrap namespaces do not match Application destinations: {environment}")
    common = read_yaml(ROOT / "argocd/bootstrap/common/argo-cd-install-values.yaml")
    override = read_yaml(bootstrap / "install/argo-cd-install-values.yaml")
    insecure = override.get("configs", {}).get("params", {}).get("server.insecure", common["configs"]["params"]["server.insecure"])
    require(insecure is False, f"Argo CD TLS must be enabled: {environment}")
    if environment == "prod":
        service = {**common["server"]["service"], **override["server"]["service"]}
        require(service["type"] == "ClusterIP" and not service.get("externalIPs"), "Prod Argo CD must not expose an external Service")


def render_external(app):
    source = app["spec"]["source"]
    helm = source["helm"]
    require(set(helm) <= {"releaseName", "skipCrds", "values"},
            f"Unsupported external Helm configuration: {app['metadata']['name']}")
    require(helm.get("skipCrds") is True, "External controller must not install CRDs")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as values:
        values.write(helm["values"])
        values.flush()
        output = run_helm([
            "template", helm["releaseName"], source["chart"], "--repo", source["repoURL"],
            "--version", str(source["targetRevision"]), "--namespace", app["spec"]["destination"]["namespace"],
            "--kube-version", "1.35.1", "--skip-crds", "-f", values.name,
        ])
    return [doc for doc in yaml.safe_load_all(output) if doc]


def validate_resources(app, project, resources, ingress_class):
    namespace = app["spec"]["destination"]["namespace"]
    identities = set()
    for resource in resources:
        metadata = resource["metadata"]
        identity = (resource["kind"], metadata.get("namespace"), metadata["name"])
        require(identity not in identities, f"Duplicate resource: {identity}")
        identities.add(identity)
        cluster_scoped = resource["kind"] in {"IngressClass", "ClusterRole", "ClusterRoleBinding"}
        if not cluster_scoped:
            require(metadata.get("namespace") == namespace, f"Wrong namespace: {identity}")
        whitelist = "clusterResourceWhitelist" if cluster_scoped else "namespaceResourceWhitelist"
        require(allowed(resource, project["spec"][whitelist]), f"Project disallows {identity}")

    deployments = [r for r in resources if r["kind"] == "Deployment"]
    services = {r["metadata"]["name"]: r for r in resources if r["kind"] == "Service"}
    for deployment in deployments:
        spec = deployment["spec"]
        labels = spec["template"]["metadata"]["labels"]
        require(all(labels.get(k) == v for k, v in spec["selector"]["matchLabels"].items()), "Deployment selector does not match pod labels")
        for container in spec["template"]["spec"]["containers"]:
            env = container.get("env", [])
            require(len({e["name"] for e in env}) == len(env), "Duplicate container environment variable")
            if container["name"] == "api":
                server_port = next(e["value"] for e in env if e["name"] == "SERVER_PORT")
                require(str(container["ports"][0]["containerPort"]) == server_port, "SERVER_PORT does not match containerPort")

    for service in services.values():
        selected = [d for d in deployments if all(
            d["spec"]["template"]["metadata"]["labels"].get(k) == v
            for k, v in service["spec"]["selector"].items()
        )]
        require(selected, f"Service {service['metadata']['name']} selects no Deployment")
        for deployment in selected:
            ports = [p for c in deployment["spec"]["template"]["spec"]["containers"] for p in c.get("ports", [])]
            for port in service["spec"]["ports"]:
                target = port["targetPort"]
                require(any(p.get("name") == target if isinstance(target, str) else p["containerPort"] == target for p in ports), f"Service targetPort {target} does not exist")

    for ingress in (r for r in resources if r["kind"] == "Ingress"):
        require(ingress["spec"]["ingressClassName"] == ingress_class, "Wrong environment ingress class")
        for rule in ingress["spec"]["rules"]:
            for path in rule["http"]["paths"]:
                backend = path["backend"]["service"]
                require(backend["name"] in services, f"Ingress backend {backend['name']} does not exist")
                ports = services[backend["name"]]["spec"]["ports"]
                require(any(p.get("name") == backend["port"].get("name") if "name" in backend["port"] else p["port"] == backend["port"]["number"] for p in ports), "Ingress references an unknown Service port")


def validate(fixtures=False, external_charts=False):
    count = 0
    for environment, revision in REVISIONS.items():
        project_paths = declaration_paths(ROOT / "argocd/projects" / environment)
        project_paths.append(ROOT / "argocd/bootstrap" / environment / "roots/root-applications-permissions.yaml")
        projects = {}
        for path in project_paths:
            project = read_yaml(path)
            name = project["metadata"]["name"]
            require(project["kind"] == "AppProject" and name not in projects, f"Invalid or duplicate project: {path}")
            require(project["metadata"].get("namespace") == "argocd", f"Wrong AppProject namespace: {path}")
            for whitelist in ("clusterResourceWhitelist", "namespaceResourceWhitelist"):
                require(all("*" not in entry.values() for entry in project["spec"].get(whitelist, [])), f"Wildcard resource permission: {path}")
            projects[name] = project

        app_paths = declaration_paths(ROOT / "argocd/applications" / environment)
        app_paths += list((ROOT / "argocd/bootstrap" / environment / "roots").glob("*-root.yaml"))
        apps = {}
        for path in app_paths:
            app = read_yaml(path)
            name = app["metadata"]["name"]
            require(app["kind"] == "Application" and name not in apps, f"Invalid or duplicate Application: {path}")
            apps[name] = app
            spec = app["spec"]
            require(app["metadata"]["namespace"] == "argocd", f"Wrong Argo CD namespace: {path}")
            require(spec["project"] in projects, f"Missing AppProject for {path}")
            project = projects[spec["project"]]["spec"]
            require(spec["source"]["repoURL"] in project["sourceRepos"], f"Disallowed source repository: {path}")
            require(spec["destination"] in project["destinations"], f"Disallowed destination: {path}")
            require("ServerSideDiff=true" not in spec["syncPolicy"].get("syncOptions", []), f"ServerSideDiff must be an annotation: {path}")
            if "path" in spec["source"]:
                require(spec["source"]["targetRevision"] == revision, f"Wrong environment revision: {path}")
            if path.is_relative_to(ROOT / "argocd/applications"):
                validate_sync_policy(spec, environment)
            count += 1

        validate_bootstrap(environment, apps)
        for kind in ("applications", "projects"):
            root = apps[f"{kind}-{environment}"]
            source = root["spec"]["source"]
            require(source["path"] == f"argocd/{kind}/{environment}" and source["directory"]["recurse"] is True, "Root must watch only its environment subtree")
            require(root["spec"]["syncPolicy"]["automated"] == {"prune": False, "selfHeal": True}, "Root deletion must require explicit prune")
            managed = (apps.values() if kind == "applications" else projects.values())
            root_project = projects[root["spec"]["project"]]["spec"]
            require(all(allowed(r, root_project["namespaceResourceWhitelist"]) for r in managed), "Root project cannot manage its declarations")

        ingress = apps[f"traefik-{environment}"]
        controller = yaml.safe_load(ingress["spec"]["source"]["helm"]["values"])
        ingress_class = controller["ingressClass"]["name"]
        require(ingress_class == f"traefik-{environment}", "Wrong controller ingress class")
        provider = controller["providers"]["kubernetesIngress"]
        require(provider["ingressClass"] == ingress_class and provider["namespaces"] == [f"farm-market-{environment}"], "Wrong controller watch scope")
        for app in apps.values():
            source = app["spec"]["source"]
            if "chart" in source and external_charts:
                resources = render_external(app)
            elif source.get("path", "").startswith("charts/"):
                chart, arguments = chart_arguments(app, fixtures)
                run_helm(["lint", chart, "--strict", *arguments])
                resources = render(app, fixtures)
            else:
                continue
            validate_resources(app, projects[app["spec"]["project"]], resources, ingress_class)
            print(f"OK: {app['metadata']['name']} ({len(resources)} resources)")
    print(f"OK: {count} Argo CD Applications and their project/source/destination contracts")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", action="store_true", help="Fill unpublished images only for offline structural checks; not deployment validation")
    parser.add_argument("--external-charts", action="store_true", help="Download and render pinned external Helm charts too (requires network)")
    args = parser.parse_args()
    if args.fixtures:
        print("STRUCTURE ONLY: unpublished images use registry.invalid fixtures; no live deployment checks.")
    if not args.external_charts:
        print("External Helm rendering skipped; use --external-charts to include it.")
    try:
        validate(args.fixtures, args.external_charts)
    except (ValueError, KeyError, OSError, subprocess.TimeoutExpired, yaml.YAMLError) as error:
        sys.exit(f"Validation failed: {error}")
