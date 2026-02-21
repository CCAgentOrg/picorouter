# LATER.md - Future Work

## Android/Termux Support
- Add setup instructions for running PicoRouter on Android via Termux or Pydroid3
- Document no-root required approach

## Privacy & ZDR Routing
- Implement auto-detection of ZDR models from OpenRouter API
- Add detailed pricing (input/output/cache) to model metadata
- Update `picorouter/privacy` virtual provider to route through ZDR models
- Add CLI commands for model sync and pricing lookup
- See docs/privacy-routing.md for full design

## Green / Climate-Aware Routing
- Research: Which LLM providers offer carbon-neutral / green compute?
- Design virtual provider: `picorouter/green` - route to lowest-carbon providers
- Track token usage per provider for carbon footprint estimation
- Consider factors:
  - Provider data center location (renewable energy)
  - Model efficiency (tokens per watt)
  - Carbon intensity APIs (optional integration)
- Add `--carbon` flag to stats showing estimated CO2
- Research sources:
  - Cloud provider sustainability docs (AWS, GCP, Azure, Cloudflare)
  - Model-specific efficiency data
  - Green Web Foundation datasets
