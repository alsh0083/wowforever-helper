# WoW Forever mage dashboard

Open `index.html` in a browser. It works offline: talent icons and all data are embedded.

**It's generated; don't edit `index.html` by hand.** Change `template.html`, the builds in `config/builds/`, or the data, then rebuild:

```sh
python -m wowforever update                                     # fetch + normalize the latest Forever build
python -m wowforever report --dataset data/datasets/<build>.json
python -m wowforever dashboard                                  # writes dashboard/index.html
```

- **Build switcher:** the current Elementalist route plus deep Frost, deep Fire and an Arcane reference build, each with its point order, scenario scores at levels 20-60, sensitivity to unknown mechanics, and caveats.
- **Progress** is saved per build in this browser (localStorage). The Elementalist build keeps the original `wow-forever-elementalist-v4` save, including migration from older versions.
- Talent text and icons: [wowforevertalent.com](https://wowforevertalent.com/) (Creative Commons Attribution). Game data: wago.tools. Artwork belongs to its respective owners.
