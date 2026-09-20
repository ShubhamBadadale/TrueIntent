from pathlib import Path

from mcdc.compiler import compile_file


def test_gcp_backend_generates_references():
    result = compile_file(Path("examples/two_tier_app.mcd"), "gcp")
    text = result.outputs["gcp"].text
    assert 'resource "google_compute_network" "main"' in text
    assert "subnetwork = google_compute_subnetwork.app.id" in text
