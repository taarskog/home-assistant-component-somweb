# Somweb

[![GitHub Release][releases-shield]][releases]
[![hacs][hacsbadge]][hacs]

<!-- [![GitHub Activity][commits-shield]][commits] -->
<!-- [![License][license-shield]](LICENSE) -->

<!-- ![Project Maintenance][maintenance-shield] -->
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]
[![Donate][paypalmebadge]][paypalme]

<!-- [![Discord][discord-shield]][discord] -->
<!-- [![Community Forum][forum-shield]][forum] -->

_Custom component for Home Assistant to manage garage doors and gates by [Sommer][sommer] through [SOMweb][sommer-somweb]_


{% if not installed %}
## Installation

1. Click install.
1. Restart Home Assistant.
{% endif %}

## Configuration

[![Add Integration][add-integration-badge]][add-integration]

or in the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Somweb".

**Fill** inn the fields specifying UDI or URL based on the chosen access mode.

**Submit** and you are done!

### Access Modes
- **Cloud Access:** The integration can use SOMweb cloud services. The required UDI number is printed on the back of the SOMweb device

- **Local Access:** Use Local access if your SOMweb device has a static IP or can be accessed using a FQDN. In this mode internet access is not required. A valid URL is required so for IP you must prefix with `http://`.


## Acknowledgements

[Blueprint][blueprint-repo] has been a great template and inspiration when setting up this repository to work with [Hacs][hacs].

***

[sommer]: https://www.sommer.eu
[sommer-somweb]: https://www.sommer.eu/en/somweb.html

[buymecoffee]: https://www.buymeacoffee.com/taarskog
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge

[paypalme]: https://paypal.me/taarskog
[paypalmebadge]: https://img.shields.io/badge/Donate-PayPal-blue.svg?style=for-the-badge

[commits-shield]: https://img.shields.io/github/commit-activity/y/taarskog/home-assistant-component-somweb.svg?style=for-the-badge
[commits]: https://github.com/taarskog/home-assistant-component-somweb/commits/main

[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge

[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge

[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/

[license-shield]: https://img.shields.io/github/license/taarskog/home-assistant-component-somweb.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Trond%20Aarskog%20%40taarskog-blue.svg?style=for-the-badge

[releases-shield]: https://img.shields.io/github/release/taarskog/home-assistant-component-somweb.svg?style=for-the-badge
[releases]: https://github.com/taarskog/home-assistant-component-somweb/releases

[blueprint-repo]: https://github.com/ludeeus/integration_blueprint
