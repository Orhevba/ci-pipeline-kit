# Self-hosted runner (k3s)

One GitHub Actions runner as a pod, for when the free tier's hosted minutes run
out. Used by `Orhevba/purser-shell` (label `k3s`); the reusable
`docker-build-push.yml` takes a `runs-on` input so callers can point at it.

- `kubectl apply -f runner.yaml` creates the `actions-runner` namespace, a 30Gi
  PVC (runner registration + Docker layer cache) and the Deployment.
- The pod is the runner plus a **privileged** `docker:dind` sidecar. They share
  a Unix socket only; never expose dockerd over TCP (that is root on the node).
- First start needs a registration token (valid one hour, used once):

  ```
  gh api -X POST repos/Orhevba/purser-shell/actions/runners/registration-token --jq .token \
    | tr -d '\n' | kubectl -n actions-runner create secret generic runner-registration --from-file=token=/dev/stdin
  ```

  The credentials it yields are saved on the PVC, so restarts do not need a new
  token, and the Secret can be deleted afterwards.
- Only run it for private repos: any workflow that can run on it gets a
  privileged container on the node.
- To go back to hosted runners, drop the `runs-on:` overrides in the caller.
