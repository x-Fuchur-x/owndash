from owndash.sensors.catalog import METRICS, metric_definition, read_metric


def test_metric_catalog_has_core_metrics():
    keys = {item.key for item in METRICS}
    assert {"cpu.usage", "gpu.usage", "temperature.value", "memory.percent"} <= keys


def test_read_metric_nested_value():
    snapshot = {"cpu": {"usage": 42.5}}
    assert read_metric(snapshot, "cpu.usage") == 42.5
    assert read_metric(snapshot, "cpu.missing") is None


def test_metric_definition_lookup():
    metric = metric_definition("gpu.temperature")
    assert metric is not None
    assert metric.unit == "°C"
