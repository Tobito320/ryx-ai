# Zen Browser Research

## Zen Browser feature/strength TODOs
- [ ] Vertical tab sidebar with pin/group/anchor options for heavy tab workflows
- [ ] Workspaces/Spaces to compartmentalize tasks (Arc/Opera-style)
- [ ] Split view layouts (side-by-side or tiled tabs) for multitasking
- [ ] Focus/Zen mode to hide chrome and reduce distractions; configurable via Zen Mods
- [ ] Sidebar web panels and “Zen Glance” previews for quick access
- [ ] Command bar for fast navigation/search beyond the URL bar
- [ ] Theme store + Zen Mods for deep UI customization (CSS tweaks, rounded corners off, etc.)
- [ ] Full Firefox extension compatibility while keeping privacy defaults
- [ ] Privacy-first defaults and cross-platform availability (Linux/macOS/Windows)

## Zen Browser weaknesses
- Slightly slower benchmarks than Chromium browsers and a bit behind Firefox in some tests
- Alpha/Beta maturity leads to occasional bugs and rough edges
- Limited/no built-in AI features compared to Edge/Arc
- Rapid feature changes/renames can cause user confusion
- Modern UI may not appeal to all users

## RyxSurf gaps/weaknesses vs. Firefox
- URL navigation reliability is still under investigation (P0 “Critical” item in `ryxsurf/PROGRESS.md`); Firefox navigation is mature.
- Workspaces are placed in the sidebar instead of the URL bar (P1 requirement in `ryxsurf/PROGRESS.md`); Firefox doesn’t have workspaces but its toolbar layout is stable and predictable.
- Layout breaks when the URL bar is hidden; Firefox handles toolbar toggles without sidebar expansion issues.
- Session restore reliability and performance are flagged (slow startup, 4s load); Firefox has stable session restore and optimized startup.
- Reader mode is not yet implemented (planned Phase 3), while Firefox ships a full reader view.
- Firefox extension ecosystem is production-ready; RyxSurf’s WebExtensions support is still noted as “planned”/incomplete in `ryxsurf/README.md`.

## Sources
- Lifehacker overview of Zen’s Arc-like features and Firefox base: https://lifehacker.com/tech/zen-is-a-firefox-based-browser-with-arcs-best-features
- ZDNet deep dive on customization/Zen Mods: https://www.zdnet.com/home-and-office/work-life/zen-browser-is-the-customizable-firefox-ive-been-waiting-for/
- AlternativeTo feature roundup: https://alternativeto.net/software/zen-browser/about/
- TechHut split-view/focus coverage: https://techhut.tv/zen-browser-better-firefox/
- XDA Developers hands-on: https://www.xda-developers.com/zen-browser-better-brave-arc-chrome/
- Geeky Gadgets privacy focus: https://www.geeky-gadgets.com/zen-browser-privacy-focused-open-source-alternative-to-chrome-and-firefox/
- Jitbit benchmarks vs. Chrome/Brave/Firefox: https://www.jitbit.com/alexblog/zen-review-benchmark/
