#!/usr/bin/env python3
"""One-shot, re-runnable deployer: LoadPilot -> Vertex AI Agent Engine -> Gemini Enterprise.

Provisions everything the agent needs, idempotently:
  1. Enables APIs (Vertex AI, Cloud Storage, Discovery Engine, IAM Credentials, Resource Manager).
  2. Buckets: staging (gs://<project>-agent-staging) and media (gs://<project>-loadpilot-media).
  3. Runtime service account loadpilot-agent@<project>.iam.gserviceaccount.com with
     aiplatform.user, logging.logWriter, storage.objectAdmin (media bucket) and
     iam.serviceAccountTokenCreator on itself (V4 signed URLs for the loader video / HTML).
  4. Deploys the ADK app to Agent Engine, or UPDATES THE SAME ENGINE IN PLACE
     (.reasoning_engine_id / display-name match) — never creates duplicates.
  5. Registers (or PATCHes) the agent in every Gemini Enterprise app found in the project
     (or the one given with --gemini-app-id), with icon + starter prompts.

Usage:
  uv run python scripts/deploy_to_gemini_enterprise.py --project my-proj [--region us-central1]
      [--gemini-app-id my-ge-app] [--viewer-domain example.com] [--skip-ge] [--skip-iam]

Auth (first that works): --token / $GCP_ACCESS_TOKEN, service-account key
($GOOGLE_APPLICATION_CREDENTIALS), ~/.config/gcloud/argolis_admin_adc.json, default ADC,
`gcloud auth print-access-token`.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import google.auth  # noqa: E402
import google.oauth2.credentials  # noqa: E402
from google.auth.transport.requests import Request  # noqa: E402

DISPLAY_NAME = "LoadPilot - Truck Load & Route Optimizer"
GE_DISPLAY_NAME = "LoadPilot Dispatch Co-pilot"
DESCRIPTION = ("LoadPilot plans daily truck dispatch for retail / CPG: corridor routes, driver claims with "
               "trunk-and-branch splitting, LIFO truck loading (first drop at the door) with 3D "
               "animation + loader video, and cost savings vs today's manual plan.")
SA_ID = "loadpilot-agent"
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
_TOKEN_OVERRIDE: str | None = None


# ==============================================================================
# Auth
# ==============================================================================
def get_credentials():
    if _TOKEN_OVERRIDE or os.environ.get("GCP_ACCESS_TOKEN"):
        return google.oauth2.credentials.Credentials(_TOKEN_OVERRIDE or os.environ["GCP_ACCESS_TOKEN"])
    sa = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if sa and Path(sa).exists() and json.loads(Path(sa).read_text()).get("type") == "service_account":
        from google.oauth2 import service_account
        c = service_account.Credentials.from_service_account_file(sa, scopes=SCOPES)
        c.refresh(Request())
        return c
    for p in (Path.home() / ".config/gcloud/argolis_admin_adc.json",
              Path.home() / ".config/gcloud/application_default_credentials.json"):
        if p.exists():
            try:
                c = google.oauth2.credentials.Credentials.from_authorized_user_file(str(p), scopes=SCOPES)
                c.refresh(Request())
                return c
            except Exception:
                continue
    tok = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True,
                                  stderr=subprocess.DEVNULL).strip()
    return google.oauth2.credentials.Credentials(tok)


_CREDS = None


def creds():
    global _CREDS
    if _CREDS is None:
        _CREDS = get_credentials()
    return _CREDS


google.auth.default = lambda *a, **k: (creds(), os.environ.get("GOOGLE_CLOUD_PROJECT"))


def api(method: str, url: str, body: dict | None = None, project: str | None = None,
        ok404: bool = False) -> dict:
    headers = {"Authorization": f"Bearer {creds().token}", "Content-Type": "application/json"}
    if project:
        headers["X-Goog-User-Project"] = project
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        txt = e.read().decode(errors="ignore")
        if ok404 and e.code == 404:
            return {"_404": True}
        raise RuntimeError(f"{method} {url} -> {e.code}: {txt[:400]}") from None


# ==============================================================================
# Resources
# ==============================================================================
def enable_apis(project: str) -> None:
    services = ["aiplatform.googleapis.com", "storage.googleapis.com", "discoveryengine.googleapis.com",
                "iamcredentials.googleapis.com", "iam.googleapis.com",
                "cloudresourcemanager.googleapis.com", "logging.googleapis.com", "routes.googleapis.com"]
    try:
        op = api("POST", f"https://serviceusage.googleapis.com/v1/projects/{project}/services:batchEnable",
                 {"serviceIds": services}, project)
        print(f"[OK] APIs enabled ({len(services)}) {op.get('name', '')}")
    except RuntimeError as e:
        print(f"[WARN] could not enable APIs (may already be enabled): {str(e)[:160]}")


def project_number(project: str) -> str:
    return api("GET", f"https://cloudresourcemanager.googleapis.com/v1/projects/{project}")["projectNumber"]


def ensure_bucket(project: str, region: str, name: str) -> str:
    r = api("GET", f"https://storage.googleapis.com/storage/v1/b/{name}", ok404=True)
    if r.get("_404"):
        api("POST", f"https://storage.googleapis.com/storage/v1/b?project={project}",
            {"name": name, "location": region, "iamConfiguration": {
                "uniformBucketLevelAccess": {"enabled": True}}})
        print(f"[CREATED] gs://{name} ({region})")
    else:
        print(f"[OK] gs://{name}")
    return name


def ensure_service_account(project: str) -> str:
    email = f"{SA_ID}@{project}.iam.gserviceaccount.com"
    r = api("GET", f"https://iam.googleapis.com/v1/projects/{project}/serviceAccounts/{email}", ok404=True)
    if r.get("_404"):
        api("POST", f"https://iam.googleapis.com/v1/projects/{project}/serviceAccounts",
            {"accountId": SA_ID, "serviceAccount": {"displayName": "LoadPilot Agent Engine runtime"}})
        print(f"[CREATED] service account {email}")
        time.sleep(8)
    else:
        print(f"[OK] service account {email}")
    return email


def _add_binding(policy: dict, role: str, member: str) -> bool:
    for b in policy.setdefault("bindings", []):
        if b["role"] == role:
            if member in b.get("members", []):
                return False
            b.setdefault("members", []).append(member)
            return True
    policy["bindings"].append({"role": role, "members": [member]})
    return True


def grant_iam(project: str, sa_email: str, media: str, viewer_domain: str | None) -> None:
    member = f"serviceAccount:{sa_email}"
    pnum = project_number(project)
    re_agent = f"serviceAccount:service-{pnum}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
    # project roles
    pol = api("POST", f"https://cloudresourcemanager.googleapis.com/v1/projects/{project}:getIamPolicy",
              {"options": {"requestedPolicyVersion": 3}})
    changed = False
    for role in ("roles/aiplatform.user", "roles/logging.logWriter", "roles/serviceusage.serviceUsageConsumer",
                 "roles/storage.objectViewer"):
        changed |= _add_binding(pol, role, member)
    if changed:
        api("POST", f"https://cloudresourcemanager.googleapis.com/v1/projects/{project}:setIamPolicy",
            {"policy": pol})
    # media bucket: runtime SA writes; RE service agent too; optional domain viewers (auth-URL fallback)
    bpol = api("GET", f"https://storage.googleapis.com/storage/v1/b/{media}/iam?optionsRequestedPolicyVersion=3")
    bchanged = _add_binding(bpol, "roles/storage.objectAdmin", member)
    bchanged |= _add_binding(bpol, "roles/storage.objectAdmin", re_agent)
    if viewer_domain:
        bchanged |= _add_binding(bpol, "roles/storage.objectViewer", f"domain:{viewer_domain}")
    if bchanged:
        api("PUT", f"https://storage.googleapis.com/storage/v1/b/{media}/iam", bpol)
    # SA can sign blobs as itself (V4 signed URLs)
    sa_res = f"https://iam.googleapis.com/v1/projects/{project}/serviceAccounts/{sa_email}"
    spol = api("POST", f"{sa_res}:getIamPolicy", {})
    if _add_binding(spol, "roles/iam.serviceAccountTokenCreator", member):
        api("POST", f"{sa_res}:setIamPolicy", {"policy": spol})
    print(f"[OK] IAM: runtime SA roles, media bucket access, self token-creator"
          + (f", viewers domain:{viewer_domain}" if viewer_domain else ""))


# ==============================================================================
# Agent Engine
# ==============================================================================
REQUIREMENTS = [
    "google-cloud-aiplatform[agent_engines,adk]>=1.160.0",
    "google-adk>=2.6.0,<3.0.0",
    "google-genai>=1.20.0",
    "google-cloud-storage>=2.18.0,<4.0.0",
    "a2a-sdk>=0.3.0",
    "numpy>=1.26,<3.0",
    "pillow>=10.0.0",
    "ortools>=9.10",
    "pandas>=2.2",
    "openpyxl>=3.1",
    "pypdf>=4.0",
    "qrcode>=7.4",
    "opencv-python-headless>=4.9",
    "imageio>=2.34",
    "imageio-ffmpeg>=0.5",
]


def deploy_engine(project: str, region: str, staging: str, sa_email: str | None, media: str,
                  model: str) -> str:
    os.environ.update({"GOOGLE_GENAI_USE_VERTEXAI": "TRUE", "GOOGLE_CLOUD_PROJECT": project,
                       "GOOGLE_CLOUD_LOCATION": region, "LOADPILOT_MODEL": model,
                       "LOADPILOT_MEDIA_BUCKET": media})
    import vertexai
    from vertexai import agent_engines

    from app.integration.agent import LoadPilotAdkApp, root_agent

    vertexai.init(project=project, location=region, staging_bucket=f"gs://{staging}", credentials=creds())
    adk_app = LoadPilotAdkApp(agent=root_agent, enable_tracing=True)
    env_vars = {"GOOGLE_GENAI_USE_VERTEXAI": "TRUE", "LOADPILOT_MODEL": model,
                "LOADPILOT_MEDIA_BUCKET": media, "LOADPILOT_UI_MODE": os.environ.get("LOADPILOT_UI_MODE", "canvas")}
    kwargs = dict(agent_engine=adk_app, requirements=REQUIREMENTS, extra_packages=["app"],
                  display_name=DISPLAY_NAME, description=DESCRIPTION, env_vars=env_vars,
                  resource_limits={"cpu": "4", "memory": "8Gi"}, min_instances=1)
    if sa_email:
        kwargs["service_account"] = sa_email

    state = ROOT / ".reasoning_engine_id"
    existing = None
    if state.exists():
        try:
            existing = agent_engines.get(state.read_text().strip()).resource_name
        except Exception:
            existing = None
    if not existing:
        for eng in agent_engines.list():
            if getattr(eng, "display_name", "") == DISPLAY_NAME:
                existing = eng.resource_name
                break
    t0 = time.time()
    if existing:
        print(f"[UPDATING IN PLACE] {existing}")
        eng = agent_engines.get(existing).update(**kwargs)
    else:
        print(f"[CREATING] Agent Engine '{DISPLAY_NAME}' in {project}/{region} ...")
        eng = agent_engines.create(**kwargs)
    res = eng.resource_name
    state.write_text(res)
    (ROOT / "deployment_metadata.json").write_text(json.dumps({
        "project_id": project, "region": region, "reasoning_engine_resource_name": res,
        "service_account": sa_email, "media_bucket": media, "agent_framework": "google-adk",
        "deployed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, indent=2) + "\n")
    eid = res.rsplit("/", 1)[-1]
    print(f"[OK] Agent Engine ready in {time.time() - t0:.0f}s: {res}")
    print(f"     Playground: https://console.cloud.google.com/vertex-ai/agents/agent-engines/locations/"
          f"{region}/agent-engines/{eid}/playground?project={project}")
    return res


# ==============================================================================
# Gemini Enterprise
# ==============================================================================
STARTERS = [
    "Plan today's dispatch from Bhiwandi with the default fleet",
    "Show me the planning form",
    "Ravi has the West route and Imran takes North-East, re-plan",
    "Show T17-1's loading plan and loader video",
]


def register_gemini_enterprise(project: str, engine: str, app_id: str | None, app_loc: str) -> None:
    targets: list[tuple[str, str]] = []
    if app_id:
        targets.append((app_loc, app_id))
    else:
        for loc in ("global", "us", "eu"):
            host = "discoveryengine.googleapis.com" if loc == "global" else f"{loc}-discoveryengine.googleapis.com"
            try:
                data = api("GET", f"https://{host}/v1alpha/projects/{project}/locations/{loc}/collections/"
                                  f"default_collection/engines", project=project)
            except RuntimeError:
                continue
            for e in data.get("engines", []):
                if e.get("solutionType", "SOLUTION_TYPE_SEARCH") in ("SOLUTION_TYPE_SEARCH", "SOLUTION_TYPE_CHAT") \
                        or "appType" in e:
                    targets.append((loc, e["name"].rsplit("/", 1)[-1]))
    if not targets:
        print(f"[INFO] No Gemini Enterprise app found. Add the agent manually with engine: {engine}")
        return
    payload = {
        "displayName": GE_DISPLAY_NAME,
        "description": DESCRIPTION,
        "icon": {"uri": "https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/local_shipping/default/24px.svg"},
        "starterPrompts": [{"text": t} for t in STARTERS],
        "adkAgentDefinition": {
            "toolSettings": {"toolDescription": "Use LoadPilot to plan truck dispatch: corridor routes, "
                                                "driver claims, LIFO truck loading and cost savings."},
            "provisionedReasoningEngine": {"reasoningEngine": engine},
        },
    }
    for loc, eid in targets:
        host = "discoveryengine.googleapis.com" if loc == "global" else f"{loc}-discoveryengine.googleapis.com"
        base = (f"https://{host}/v1alpha/projects/{project}/locations/{loc}/collections/default_collection/"
                f"engines/{eid}/assistants/default_assistant/agents")
        try:
            agents = api("GET", base, project=project).get("agents", [])
            cur = next((a["name"] for a in agents if a.get("displayName") == GE_DISPLAY_NAME), None)
            if cur:
                res = api("PATCH", f"https://{host}/v1alpha/{cur}?updateMask=displayName,description,icon,"
                                   "starterPrompts,adkAgentDefinition", {**payload, "name": cur}, project)
                print(f"[OK] Gemini Enterprise '{eid}' ({loc}): updated {res.get('name', cur)}")
            else:
                res = api("POST", base, payload, project)
                print(f"[OK] Gemini Enterprise '{eid}' ({loc}): registered {res.get('name')}")
        except RuntimeError as e:
            print(f"[NOTE] Gemini Enterprise '{eid}' ({loc}): {str(e)[:300]}")


def main() -> None:
    global _TOKEN_OVERRIDE
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=os.environ.get("GOOGLE_CLOUD_PROJECT", "zuhaibp-ai"))
    ap.add_argument("--region", default="us-central1")
    ap.add_argument("--model", default="gemini-2.5-flash")
    ap.add_argument("--gemini-app-id", default="")
    ap.add_argument("--gemini-app-location", default="global")
    ap.add_argument("--viewer-domain", default="", help="Domain allowed to open media links (fallback)")
    ap.add_argument("--token", default="", help="OAuth access token to use for all calls")
    ap.add_argument("--skip-iam", action="store_true")
    ap.add_argument("--skip-ge", action="store_true")
    ap.add_argument("--no-custom-sa", action="store_true", help="Use the default Agent Engine service agent")
    a = ap.parse_args()
    _TOKEN_OVERRIDE = a.token or None
    os.environ["GOOGLE_CLOUD_PROJECT"] = a.project

    enable_apis(a.project)
    staging = ensure_bucket(a.project, a.region, f"{a.project}-agent-staging")
    media = ensure_bucket(a.project, a.region, f"{a.project}-loadpilot-media")
    sa = None
    if not a.no_custom_sa:
        sa = ensure_service_account(a.project)
    if not a.skip_iam and sa:
        grant_iam(a.project, sa, media, a.viewer_domain or None)
    engine = deploy_engine(a.project, a.region, staging, sa, media, a.model)
    if not a.skip_ge:
        register_gemini_enterprise(a.project, engine, a.gemini_app_id or None, a.gemini_app_location)


if __name__ == "__main__":
    main()
