# OwnDash public beta release checklist

## Code freeze
- [ ] All automated tests pass.
- [ ] No new editor features after release candidate is cut.
- [ ] Dark, Light and System appearance checked.
- [ ] German and English UI checked.

## Clean-user test
- [ ] Download only the AppImage on a clean user account / test system.
- [ ] AppImage starts without Python or pip installed by the user.
- [ ] First-run system check is readable at normal and scaled desktop settings.
- [ ] Standard-monitor output works and Esc/F11 exits safely.
- [ ] ArtInChip/VSDISPLAY detection is understandable.
- [ ] USB permission button opens normal administrator authentication.
- [ ] Reconnect display and verify direct USB output.
- [ ] Widget selection survives Breathe/other animations.
- [ ] Save/load profile.
- [ ] Close-to-tray and reopen.
- [ ] Second launch activates the existing instance.

## GitHub
- [ ] README screenshots updated.
- [ ] CHANGELOG reviewed.
- [ ] LICENSE and THIRD_PARTY present.
- [ ] Issue template works.
- [ ] AppImage attached to the GitHub Release.
- [ ] SHA-256 published.
- [ ] Release notes list tested system and known limitations.
