from pathlib import Path

from mcdc.compiler import compile_file


def test_azure_backend_generates_references():
    result = compile_file(Path("examples/network_only.mcd"), "azure")
    text = result.outputs["azure"].text
    assert 'resource "azurerm_virtual_network" "main"' in text
    assert "virtual_network_name = azurerm_virtual_network.main.name" in text
