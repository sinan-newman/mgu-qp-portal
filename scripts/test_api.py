import urllib.request
import json

# 1. Fetch pending papers
req = urllib.request.urlopen("http://localhost:8080/api/admin/pending-papers")
res = json.loads(req.read().decode("utf-8"))
print(f"Pending papers count: {res['total']}")
assert res['total'] == 1, f"Expected 1 pending paper, got {res['total']}"
p = res['papers'][0]
print(f"Pending paper ID: {p['id']}, raw: {p['raw_header']}")

# 2. Test resolving with a duplicate course code (MG3DSCCOM200)
# This course already exists in semester 3!
resolve_payload = {
    "paper_id": p["id"],
    "course_code": "MG3DSCCOM200",
    "course_title": "Financial Accounting",
    "semester": 3,
    "dept_code": "COM"
}

req_resolve = urllib.request.Request(
    "http://localhost:8080/api/admin/resolve-paper",
    data=json.dumps(resolve_payload).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

with urllib.request.urlopen(req_resolve) as resp:
    res_resolve = json.loads(resp.read().decode("utf-8"))
    print("\n--- Resolution Result ---")
    print(json.dumps(res_resolve, indent=2))
    assert res_resolve["action"] == "merged", "Expected action to be 'merged' for duplicate course"
    assert res_resolve["deleted_id"] == p["id"], "Expected duplicate test paper to be deleted"

# 3. Verify pending queue is back to 0
req_after = urllib.request.urlopen("http://localhost:8080/api/admin/pending-papers")
res_after = json.loads(req_after.read().decode("utf-8"))
print(f"\nPending papers count after resolution: {res_after['total']}")
assert res_after['total'] == 0, "Pending queue should be 0"

# 4. Verify public /api/papers doesn't return deleted paper
req_search = urllib.request.urlopen("http://localhost:8080/api/papers?search=test_ambiguous")
res_search = json.loads(req_search.read().decode("utf-8"))
print(f"Public search count: {res_search['total']}")
assert res_search['total'] == 0, "Public search should not find deleted paper"

print("\nALL BACKEND API TESTS PASSED SUCCESSFULLY!")
