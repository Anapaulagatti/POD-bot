# Gemini Free Tier: models for text are not image models (November 2026)

## The original issue

PODBot's image-model dropdown only exposed Gemini model names containing image/banana. The Gemini model inventory returned by Google also includes free-tier text models, TTS, embeddings and others. The prior Gemini SEO mode used a hard-coded model, so users could not select a Gemini Free Tier text model inside Studio.

## New workflow on weak Windows PCs

1. Open Settings, choose Gemini, and press "Kiểm tra key + tải model". This performs read-only API model discovery without generating an image.
2. Open Studio and use the newly added separate "MODEL GEMINI VĂN BẢN" field. It lists only text-capable models that Google advertises as supporting generateContent; it never mistakes a text model for a PNG image model.
3. Click "Gemini viết lại prompt (chỉ văn bản)" to make ONE explicit text request and place the result in the editable prompt field. The original structured prompt provenance is cleared because AI altered its text. Review it manually.
4. Optionally select Gemini SEO and the desired text model when generating an image using an actual image provider such as Cloudflare. The SEO text model is recorded in the draft manifest.

Per Google's published pricing, gemini-3.5-flash-lite, gemini-3.1-flash-lite, gemini-2.5-flash-lite, and gemini-3.5-flash are Free Tier candidates for TEXT usage. This does not mean a particular project has Free Tier eligibility. See https://ai.google.dev/gemini-api/docs/pricing.

Google's Gemini IMAGE models have different pricing; Free Tier text models cannot return a POD PNG. The new text feature never requests IMAGE response modalities.

## Safety

The user's Gemini API key stays in memory or the optional OS credential store and is sent only as an authenticated header to the official HTTPS endpoint. Every text inference requires explicit user confirmation and local daily attempt reservation, even when the model advertises Free Tier, because a paid-tier project can incur charges. No fallback and no automatic retry.

Read-only models.list success does NOT prove an API key can perform inference. A 403 often indicates a restricted project or Free Tier unavailability. A 429 indicates per-model quota exhaustion; consult https://ai.google.dev/gemini-api/docs/troubleshooting and https://aistudio.google.com/docs/rate-limits.

CLI example with a private locally configured GEMINI_API_KEY:
    podbot gemini-text --model gemini-3.5-flash-lite --prompt "Original minimalist alpine badge on a flat magenta background" --paid-ok

The --paid-ok switch acknowledges potential billing, but is not a remote billing limit. Check the project tier before using it.

No real API key, billed request, or production print artifact was used in these unit tests. The tests mock all Google API responses and check correct model routing and security gates.
