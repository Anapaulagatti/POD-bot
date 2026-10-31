# PODBot Studio 4.0: Image provider marketplace

Verified against official provider documentation on 2026-10-31. Pricing, quotas and model access may change; results are account dependent. Tests are mocked, and no real paid API token was used to verify live generation.

## Choice catalog

| Model ID | Platform | Native model | Key environment variable | Billing |
| --- | --- | --- | --- | --- |
| cloudflare | Cloudflare Workers AI | flux-1-schnell | CLOUDFLARE_API_TOKEN (+ ACCOUNT_ID) | Limited free or account billing |
| huggingface | Hugging Face | FLUX.1-schnell | HF_TOKEN | Small free credit or billable |
| gemini-flash-lite | Google | gemini-3.1-flash-lite-image | GEMINI_API_KEY | Paid, 1K |
| gemini-flash | Google | gemini-3.1-flash-image | GEMINI_API_KEY | Paid, 1K/2K/4K |
| gemini-pro | Google | gemini-3-pro-image | GEMINI_API_KEY | Paid, 1K/2K/4K |
| openai-flare | OpenAI | gpt-image-2.5-flare | OPENAI_API_KEY | Paid, transparent PNG |
| openai-sunburst | OpenAI | gpt-image-2.5-sunburst | OPENAI_API_KEY | Paid, transparent PNG |
| replicate-schnell | Replicate | black-forest-labs/flux-schnell | REPLICATE_API_TOKEN | Paid |
| replicate-dev | Replicate | black-forest-labs/flux-dev | REPLICATE_API_TOKEN | Paid |
| fal-turbo | fal.ai | fal-ai/flux-2/turbo | FAL_KEY | Paid |
| fal-z-image | fal.ai | fal-ai/z-image/turbo | FAL_KEY | Paid |
| stability-core | Stability AI | stable-image/generate/core | STABILITY_API_KEY | Paid |
| stability-ultra | Stability AI | stable-image/generate/ultra | STABILITY_API_KEY | Paid |

Paid models require a separate confirmation in the GUI or --paid-ok per CLI invocation. Gemini SEO also requires a paid confirmation independently of whether the image provider is paid. The app does not automatically change provider after errors.

## Example

- Desktop: AI Design + SEO, select the image model and (for Gemini) 1K/2K/4K; enter its key in API Settings; approve the billable request before submitting.
- CLI: podbot models
- CLI: podbot create --provider gemini-flash --gemini-size 2K --paid-ok --seo local --niche "original flowers" --keywords "floral,flower" --prompt "Unique hand-drawn botanical art, no logo".
- No image fee: podbot import --file C:\\art\\design.png --niche "botanical" --keywords "flowers".
- The API keys stay in process memory or environment variables, not source files/manifests. This is not yet an OS key vault. Do not commit keys or share them in screenshots.

## Strategic defaults

- Limited spending: use local imports / account free allocations after verifying eligibility, or cheap hosted FLUX options. Cloudflare/HF free credits are not unlimited or guaranteed.
- Text precision and elaborate high-resolution composition: Gemini Pro Image, GPT Image 2.5 models. Examine the actual native pixels and typography; resizing never adds guaranteed detail.
- Transparent artwork: OpenAI Image API supports transparent PNG output, but inspect real alpha/background through PODBot QC.
- Stability Core/Ultra is added as a native REST connector, no Stability SDK bundled.
- Replicate polling is bounded. After a timeout, consult your account dashboard before paying to retry. fal uses synchronous REST and is not suited to queued production batches yet.
- No provider prices are hardcoded: live price, region, billing verification and quality level influence cost. No background paid retry/fallback.

## Official API sources

- Google image generation: https://ai.google.dev/gemini-api/docs/image-generation
- Google image model releases: https://ai.google.dev/gemini-api/docs/changelog
- Google pricing: https://ai.google.dev/gemini-api/docs/pricing
- OpenAI Image API: https://developers.openai.com/api/docs/guides/image-generation
- OpenAI API model reference: https://developers.openai.com/api/reference/resources/images/methods/generate
- Replicate predictions: https://replicate.com/docs/topics/predictions/create-a-prediction
- Replicate FLUX Schnell: https://replicate.com/black-forest-labs/flux-schnell/api
- fal FLUX 2 Turbo: https://fal.ai/models/fal-ai/flux-2/turbo/api
- Stability API: https://kb.stability.ai/knowledge-base/integrating-stability-ai-with-zapier

## Safety and limitations

- Model selection IDs are allowlisted. Passwords/cookies for Redbubble and TeePublic are never collected, and auto-upload remains disabled.
- CDN image URL download is restricted to trusted vendor hosts; unexpected redirects are rejected. If an API changes its CDN, update adapter after verification, do not disable URL validation.
- Only mock-based API tests have been run. Actual request contracts, billing and model license conditions require user-account testing; no API success guarantee.
- Model weights, GPU runtimes and external image processing utilities are not bundled into the Windows EXE.
