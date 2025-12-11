# Zen Browser Research

## Zen Browser feature/strength checklist (documented)
- [x] Vertical tab sidebar with pin/group/anchor options for heavy tab workflows
- [x] Workspaces/Spaces to compartmentalize tasks (Arc/Opera-style)
- [x] Split view layouts (side-by-side or tiled tabs) for multitasking
- [x] Focus/Zen mode to hide chrome and reduce distractions; configurable via Zen Mods
- [x] Sidebar web panels and “Zen Glance” previews for quick access
- [x] Command bar for fast navigation/search beyond the URL bar
- [x] Theme store + Zen Mods for deep UI customization (CSS tweaks, rounded corners off, etc.)
- [x] Full Firefox extension compatibility while keeping privacy defaults
- [x] Privacy-first defaults and cross-platform availability (Linux/macOS/Windows)

## Zen Browser weaknesses (documented)
- [x] Slightly slower benchmarks than Chromium browsers and a bit behind Firefox in some tests
- [x] Alpha/Beta maturity leads to occasional bugs and rough edges
- [x] Limited/no built-in AI features compared to Edge/Arc
- [x] Rapid feature changes/renames can cause user confusion
- [x] Modern UI may not appeal to all users

## RyxSurf gaps/weaknesses vs. Firefox (tracked)
- [ ] URL navigation reliability: still open under P0 - Critical (“[ ] URL navigation not working”; code path looks correct but needs live testing with a fresh log) in `ryxsurf/PROGRESS.md`; Firefox navigation is mature.
- [ ] Workspaces placement: sidebar instead of URL bar (P1 - High item “Workspaces in wrong location” in `ryxsurf/PROGRESS.md`); Firefox doesn’t have workspaces but its toolbar layout is stable and predictable.
- [ ] Layout stability: breaks when the URL bar is hidden; Firefox handles toolbar toggles without sidebar expansion issues.
- [ ] Session restore performance/reliability: slow startup (~4s) and flagged in PROGRESS; Firefox has stable session restore and optimized startup.
- [ ] Reader mode: listed for Phase 3 in `ryxsurf/PROGRESS.md`; Firefox ships a full reader view.
- [ ] WebExtensions support: production-ready in Firefox; RyxSurf marked planned/incomplete in `ryxsurf/README.md`.

## Sources
- Lifehacker overview of Zen’s Arc-like features and Firefox base: https://lifehacker.com/tech/zen-is-a-firefox-based-browser-with-arcs-best-features
- ZDNet deep dive on customization/Zen Mods: https://www.zdnet.com/home-and-office/work-life/zen-browser-is-the-customizable-firefox-ive-been-waiting-for/
- AlternativeTo feature roundup: https://alternativeto.net/software/zen-browser/about/
- TechHut split-view/focus coverage: https://techhut.tv/zen-browser-better-firefox/
- XDA Developers hands-on: https://www.xda-developers.com/zen-browser-better-brave-arc-chrome/
- Geeky Gadgets privacy focus: https://www.geeky-gadgets.com/zen-browser-privacy-focused-open-source-alternative-to-chrome-and-firefox/
- Jitbit benchmarks vs. Chrome/Brave/Firefox: https://www.jitbit.com/alexblog/zen-review-benchmark/
