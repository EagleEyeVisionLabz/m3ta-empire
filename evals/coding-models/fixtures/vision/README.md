# vision-to-code fixtures

Each `<case>.json` describes one mockup → HTML test:

```json
{
  "name": "single-button-page",
  "brief": "Render this single-button landing page as HTML+CSS.",
  "image": "single-button-page.png",
  "reference_html": "single-button-page.expected.html",
  "min_score": 0.6
}
```

The `image` path is relative to the case JSON. The shipped `sample.json` has a placeholder image path; drop a real PNG next to it before running with a real backend. The mock backend doesn't need the image to exist.
