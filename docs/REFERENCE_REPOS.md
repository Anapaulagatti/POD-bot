# Third-party reference repositories (reviewed October 2026)

References for architectural inspiration only. **No third-party code has been copied.** Validate license and security before importing any library or files.

| Repository | Relevant pattern | Caveat |
| --- | --- | --- |
| [KillianDoubre/redbubble-automation](https://github.com/KillianDoubre/redbubble-automation) (also accessible as Freezeraid/redbubble-automation) | prompt -> image API -> metadata -> upload pipeline | README describes Ubuntu cron + OpenAI/Replicate tokens; paid services, browser flows and account-automation limitations; LICENSE not found at root. |
| [josephmartinmoran/Automated_Print_On_Demand_Dalle](https://github.com/josephmartinmoran/Automated_Print_On_Demand_Dalle) | generation + platform asset sync | Uses DALL-E and Printify/Shopify keys; not our two target marketplaces. |
| [tommywilczek/printOnDemand](https://github.com/tommywilczek/printOnDemand) | multi-product preparation/uploader ideas | Amazon-focused; do not assume API/UI behavior matches Redbubble or TeePublic. |
| [jalbrekt85/Redbubble-Bot](https://github.com/jalbrekt85/Redbubble-Bot) | GUI with directory-based uploads | MIT license confirmed at root; account automation still needs platform-policy review. |
| [ManasiTilak/RedBubbleUploader](https://github.com/ManasiTilak/RedBubbleUploader) | direct field-filling workflow | Python automation; UI fragility and platform requirements must be verified. |
| [comfyanonymous/ComfyUI](https://github.com/comfyanonymous/ComfyUI) | future local diffusion provider | GPU weights and licensing differ by selected model; not bundled in EXE. |

## Provider selection

- Cloudflare Workers AI FLUX.1 Schnell: initial provider, quota and runtime pricing dependent on current account.
- Hugging Face Inference Providers: opt-in backup, free usage credits can be tiny.
- ComfyUI: future local option; running a local server/model is not equivalent to a self-contained lightweight EXE.
- Gemini: optional SEO drafts. User should verify API eligibility for the selected model.

No claims of guaranteed organic traffic, approval/ranking benefits or marketplace API availability are built into the application.
