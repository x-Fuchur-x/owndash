from pathlib import Path

from owndash.hardware.aic_cdc import find_control_tty


def test_find_control_tty_matches_usb_parent_vid_pid(tmp_path: Path):
    sys_class_tty = tmp_path / "sys" / "class" / "tty"
    usb_device = tmp_path / "sys" / "devices" / "usb1" / "1-1"
    interface = usb_device / "1-1:1.2"
    tty_entry = sys_class_tty / "ttyACM7"
    dev_root = tmp_path / "dev"

    interface.mkdir(parents=True)
    tty_entry.mkdir(parents=True)
    dev_root.mkdir(parents=True)
    (usb_device / "idVendor").write_text("33c3\n", encoding="utf-8")
    (usb_device / "idProduct").write_text("0e02\n", encoding="utf-8")
    (tty_entry / "device").symlink_to(interface, target_is_directory=True)
    (dev_root / "ttyACM7").touch()

    assert find_control_tty(sys_class_tty, dev_root) == dev_root / "ttyACM7"


def test_find_control_tty_ignores_unrelated_usb_device(tmp_path: Path):
    sys_class_tty = tmp_path / "sys" / "class" / "tty"
    usb_device = tmp_path / "sys" / "devices" / "usb1" / "1-2"
    interface = usb_device / "1-2:1.2"
    tty_entry = sys_class_tty / "ttyACM0"
    dev_root = tmp_path / "dev"

    interface.mkdir(parents=True)
    tty_entry.mkdir(parents=True)
    dev_root.mkdir(parents=True)
    (usb_device / "idVendor").write_text("1234\n", encoding="utf-8")
    (usb_device / "idProduct").write_text("5678\n", encoding="utf-8")
    (tty_entry / "device").symlink_to(interface, target_is_directory=True)
    (dev_root / "ttyACM0").touch()

    assert find_control_tty(sys_class_tty, dev_root) is None
