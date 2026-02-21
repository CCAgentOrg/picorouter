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

## Provider Scoping Filters (`:free`, `:zdr`, etc.)
- Add scoping syntax to filter models within a provider
- Syntax: `provider:filter` where filter can be:
  - `:free` - Only free models (price = 0)
  - `:zdr` - Only ZDR/privacy-compliant models
  - `:green` - Only green/carbon-neutral models
  - `:fast` - Only low-latency models
- Examples:
  - `openrouter:free` - Free models from OpenRouter
  - `kilo:free` - Free tier from Kilo
  - `privacy:free` - Free + ZDR compliant
  - `green:free` - Free + green compute
- Implementation:
  - Parse `provider:filter` in model selection
  - Filter models based on metadata (price, zdr, green flags)
  - Fallback to all models if filter yields none
