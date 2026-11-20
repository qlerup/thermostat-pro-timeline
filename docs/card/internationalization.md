# Internationalization (languages and detection)

The card is localized and auto‑selects language by:

1) `hass.locale.language` or `hass.language` from Home Assistant
2) Browser `navigator.language`
3) Fallback: English

Normalization: underscores are converted to hyphens and lower‑cased (e.g., da_DK → da-dk). Aliases map `no → nb`, `cz → cs`, `dk → da`.

Included languages

- English (en)
- Danish (da)
- Swedish (sv)
- Norwegian Bokmål (nb)
- German (de)
- Spanish (es)
- French (fr)
- Italian (it)
- Finnish (fi)
- Czech (cs)
- Slovenian (sl)
