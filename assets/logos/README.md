# Logo Assets

Drop official brand logo PNGs here. Must have transparency (RGBA).
The compositor overlays these onto generated thumbnails — it never asks the image model to generate them.

## Expected filenames

| File | Brand |
|------|-------|
| `claude.png` | Anthropic Claude |
| `openai.png` | OpenAI / ChatGPT |
| `gemini.png` | Google Gemini |
| `cursor.png` | Cursor IDE |
| `perplexity.png` | Perplexity AI |
| `copilot.png` | GitHub Copilot |
| `grok.png` | xAI Grok |

## Source

Download official press-kit logos with transparent backgrounds.
Recommended size: at least 400×400 px, PNG with alpha channel.
The compositor auto-scales them to ~18% of thumbnail height.

## Missing assets

If a logo file is not present, the compositor silently skips it — the thumbnail generates without that overlay.
