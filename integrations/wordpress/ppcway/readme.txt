=== PPCWay ===
Contributors: ppcway
Tags: google ads, conversions, leads, analytics, call tracking
Requires at least: 5.8
Tested up to: 6.8
Requires PHP: 7.4
Stable tag: 1.0.0
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

See which ads bring customers. Counts your website's visits and leads for PPCWay, and sends the jobs they became back to Google Ads.

== Description ==

PPCWay looks after a small business's Google Ads. This plugin puts PPCWay's script on every page of your WordPress site, so PPCWay can show you:

* how many people visited, and where they came from (Google Ads, Google search, Facebook, other sites);
* who got in touch: forms sent, phone numbers and email addresses tapped;
* which leads became jobs, which you mark in PPCWay and PPCWay sends back to Google Ads against the ad click that brought them.

It works with Contact Form 7, WPForms, Elementor forms, Gravity Forms and ordinary HTML forms, and counts a form only once it has really been sent.

It never reads passwords, payment details or hidden fields. Browsers that send Global Privacy Control are counted without what was typed. It loads after your page, so it does not slow it down.

You need a PPCWay account. The key to paste is on the Website screen in PPCWay.

== Installation ==

1. Plugins, Add New, Upload Plugin: choose the zip from PPCWay, then Activate.
2. Settings, PPCWay: paste your key from the Website screen in PPCWay, and save.
3. Open any page of your site. PPCWay's Website screen says Working within a minute.

== Frequently Asked Questions ==

= Does it need my Google Ads password or access? =

No. PPCWay holds the connection to Google Ads. This plugin only tells PPCWay what happened on your site.

= My site asks visitors for cookie consent. =

Tick "Wait until the visitor agrees" and have your consent banner run `ppcway("consent")` when the visitor agrees to statistics.

== Changelog ==

= 1.0.0 =
* First release.
