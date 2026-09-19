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

## AppImage compatibility
- [ ] GitHub AppImage workflow completes successfully from the intended release tag.
- [ ] Maximum required GLIBC version is verified as GLIBC 2.36 or older.
- [ ] Finished AppImage passes the Debian 12 compatibility smoke test.
- [ ] Release asset filename matches the documented release version.

## Documentation
- [ ] `README.md` current release, tag link and AppImage filename match the release.
- [ ] `README_DE.md` current release, tag link and AppImage filename match the release.
- [ ] English and German README describe the same supported display capabilities and known limitations.
- [ ] `CHANGELOG.md` contains the release and `Unreleased` remains ready for the next development cycle.
- [ ] `ROADMAP.md` does not list already released functionality as future work.
- [ ] Release-specific notes in `docs/releases/` match the final artifact and validation status.
- [ ] LICENSE and THIRD_PARTY are present.

## GitHub release
- [ ] Tag points to the intended release commit.
- [ ] Beta releases are marked as pre-release.
- [ ] AppImage is attached to the GitHub Release.
- [ ] SHA-256 is published and matches the attached AppImage digest.
- [ ] Release notes list tested system and known limitations.
- [ ] Release-note Markdown renders correctly: headings, lists and fenced code blocks are closed.
- [ ] Download/install commands use the exact attached AppImage filename.
- [ ] Issue template works.

## Repository hygiene
- [ ] Default branch is `main`.
- [ ] Temporary release/test branches are deleted after their work is merged or superseded.
- [ ] Branch protection/rulesets for `main` still match the intended workflow.
- [ ] Automatic deletion of merged branches is enabled if supported by the repository workflow.
