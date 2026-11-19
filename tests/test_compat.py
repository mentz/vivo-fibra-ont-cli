def test_legacy_launcher_exports_main():
    import vivo_ont

    assert callable(vivo_ont.main)
    assert vivo_ont.__version__
