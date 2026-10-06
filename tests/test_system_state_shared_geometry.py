from PIL import Image, ImageChops
from PySide6.QtGui import QIcon
from owndash.core.system_state import SystemState
from owndash.gui.system_state_frame import render_system_state_image, render_disconnected_status_image


def energy(frame, box):
    # Maximum channel isolates spatial brightness from each state's hue.
    rgb = frame.convertToFormat(frame.Format.Format_RGB888)
    im = Image.frombytes('RGB', (rgb.width(), rgb.height()), bytes(rgb.constBits()), 'raw', 'RGB', rgb.bytesPerLine())
    r,g,b=im.crop(box).split()
    return ImageChops.lighter(ImageChops.lighter(r,g),b)


def test_all_states_share_frame_and_floor_geometry(qapplication):
    states=[SystemState.LOCKED,SystemState.IDLE,SystemState.SUSPENDING,SystemState.SHUTTING_DOWN,SystemState.RESTARTING]
    frames=[render_system_state_image(480,1920,s,'owndash',QIcon(),{}) for s in states]
    frames.append(render_disconnected_status_image(480,1920,QIcon()))
    # Whole side rails and floor, away from dynamic text/clock/symbol.
    for box in [(0,0,50,1920),(430,0,480,1920),(0,1500,480,1920)]:
        reference=energy(frames[0],box)
        for frame in frames[1:]:
            difference=ImageChops.difference(reference,energy(frame,box))
            assert difference.getextrema()[1] <= 2, box
