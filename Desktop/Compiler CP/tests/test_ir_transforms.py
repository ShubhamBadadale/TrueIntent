from pathlib import Path

from mcdc.compiler import build_ir
from mcdc.ir_transforms.dependency_graph import topological_order
from mcdc.ir_transforms.partition import partition_portable


def test_ir_lowering_normalizes_and_orders():
    module, diagnostics, _ = build_ir(Path("examples/static_web_server.mcd"))
    assert module is not None
    assert not [d for d in diagnostics if d.severity == "error"]
    order, diags = topological_order(module)
    assert diags == []
    assert order.index("network.main") < order.index("subnet.public")
    portable, provider_specific = partition_portable(module)
    assert len(portable) == len(module.resources)
    assert provider_specific == []
