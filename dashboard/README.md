# WoW Forever talent paths dashboard

Open `index.html` in a browser. It works offline: talent icons and all data are embedded.

**It's generated; don't edit `index.html` by hand.** Change `template.html`, the builds in `config/builds/`, or the data, then rebuild:

```sh
python -m wowforever update                                     # fetch + normalize the latest Forever build
python -m wowforever report --dataset data/datasets/<build>.json --class <class> --out data/report-<class>.json   # each class; mage writes data/report.json
python -m wowforever dashboard                                  # writes dashboard/index.html
```

- **All nine classes** (class tabs at the top): the spec matrix of community and model builds, each build's talent path (point order), its About this build text, talent layout, scores at levels 20-60 and recommended gear by level. See the main README for details.
- **Progress** is saved per build in this browser (localStorage).
- Talent text and icons: [wowforevertalent.com](https://wowforevertalent.com/) (Creative Commons Attribution). Game data: wago.tools. Artwork belongs to its respective owners.
