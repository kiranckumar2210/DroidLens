# DroidLens CLI — CI Integration

Offline validation tools for pipelines (no device required).

## Install

Uses the same Python backend as DroidLens:

```bash
cd backend && pip install -r requirements.txt
```

## Commands

```bash
# Validate locators.json against one XML dump (exit 1 on failure)
./scripts/droidlens.sh validate-locators --xml Login.xml --locators locators.json

# Validate suite against a folder of XML files
./scripts/droidlens.sh validate-folder --dir ./screens --locators locators.json

# Health scan with minimum score gate
./scripts/droidlens.sh health-scan --xml Login.xml --min-score 70 --json
```

## Locator suite format

```json
{
  "format": "droidlens-locator-suite",
  "formatVersion": 1,
  "project": "MyApp",
  "screens": [
    {
      "name": "Login",
      "xml_file": "Login.xml",
      "elements": [
        {
          "name": "login_button",
          "locator_type": "resource_id",
          "value": "com.example:id/login"
        }
      ]
    }
  ]
}
```

Download a template from the app: **Dashboard → Offline Tools → Validate Locator Suite → Template**.

## GitHub Actions example

```yaml
- name: Validate Android locators
  run: |
    pip install -r backend/requirements.txt
    ./scripts/droidlens.sh validate-folder --dir tests/fixtures/ui --locators tests/locators.json
```
