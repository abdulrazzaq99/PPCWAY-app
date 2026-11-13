/*
  PPCWay's script for a merchant's website.

  Installed as one tag:
    <script async src="https://app.ppcway.com/t.js" data-key="pw_..."></script>

  It reports two things to PPCWay: a page was viewed (with where the visit came
  from, including Google's ad click id), and somebody got in touch -- a form
  sent, a phone number or email address tapped. Nothing else: no mouse
  movements, no keystrokes, no recordings, and nothing from a form until it is
  sent.

  What is never read from a form: passwords, hidden fields, files, and any
  field named like a card number (PPCWay drops those again on arrival). A
  browser sending Global Privacy Control has its leads counted and what was
  typed left out.

  For sites that ask for consent first, add data-consent="wait" to the tag and
  call ppcway("consent") once the visitor agrees. Nothing is sent before.

  When the merchant chooses, it also fires their Google Ads conversion for a
  form or a call, so Google's own tag needs no separate set-up.
*/
(function () {
  "use strict";
  if (window.__ppcway) return;
  var me = document.currentScript || document.querySelector('script[data-key][src*="/t.js"]');
  if (!me) return;
  var key = me.getAttribute("data-key") || "";
  if (!key) return;
  window.__ppcway = true;

  var base;
  try {
    base = new URL(me.src).origin;
  } catch (e) {
    return;
  }
  var ENDPOINT = base + "/api/collect";
  var QUIET = navigator.globalPrivacyControl === true;
  var IDLE = 30 * 60 * 1000; // a visit ends after half an hour with nothing
  var started = false;
  var config = { tag: "", form: "", call: "" };

  function storage(kind) {
    try {
      var s = window[kind];
      s.setItem("__pw", "1");
      s.removeItem("__pw");
      return s;
    } catch (e) {
      return null;
    }
  }
  var local = storage("localStorage");
  var session = storage("sessionStorage");
  function read(s, k) {
    try {
      return s ? s.getItem(k) : null;
    } catch (e) {
      return null;
    }
  }
  function write(s, k, v) {
    try {
      if (s) s.setItem(k, v);
    } catch (e) {
      /* storage full or blocked: carry on without it */
    }
  }
  function newId() {
    var bytes = new Uint8Array(12);
    if (window.crypto && crypto.getRandomValues) crypto.getRandomValues(bytes);
    else for (var i = 0; i < bytes.length; i++) bytes[i] = Math.floor(Math.random() * 256);
    var out = "";
    for (var j = 0; j < bytes.length; j++) out += ("0" + bytes[j].toString(16)).slice(-2);
    return out;
  }

  var visitor = read(local, "pw_u") || newId();
  write(local, "pw_u", visitor);

  function visitId() {
    var now = Date.now();
    var held = read(session, "pw_v");
    var last = Number(read(session, "pw_t") || 0);
    if (!held || now - last > IDLE) held = newId();
    write(session, "pw_v", held);
    write(session, "pw_t", String(now));
    return held;
  }

  function device() {
    var w = window.innerWidth || screen.width || 1024;
    if (/Mobi|Android|iPhone/i.test(navigator.userAgent) || w < 768) return "mobile";
    return w < 1024 ? "tablet" : "desktop";
  }

  function send(event) {
    var body = {
      key: key,
      v: visitId(),
      u: visitor,
      d: device(),
      p: QUIET ? 1 : 0,
    };
    for (var name in event) body[name] = event[name];
    var text = JSON.stringify(body);
    try {
      if (
        navigator.sendBeacon &&
        navigator.sendBeacon(ENDPOINT, new Blob([text], { type: "text/plain" }))
      )
        return;
    } catch (e) {
      /* fall through to fetch */
    }
    try {
      fetch(ENDPOINT, {
        method: "POST",
        body: text,
        keepalive: true,
        mode: "no-cors",
        headers: { "content-type": "text/plain" },
      });
    } catch (e) {
      /* nothing more to try */
    }
  }

  // --- page views, including sites that change page without reloading -----

  var lastUrl = "";
  function viewed(referrer) {
    var url = location.href;
    if (url === lastUrl) return;
    var from = referrer == null ? lastUrl || document.referrer : referrer;
    lastUrl = url;
    send({ t: "view", url: url, r: from });
  }
  function watchNavigation() {
    ["pushState", "replaceState"].forEach(function (name) {
      var original = history[name];
      if (typeof original !== "function") return;
      history[name] = function () {
        var result = original.apply(this, arguments);
        setTimeout(function () {
          viewed(null);
        }, 0);
        return result;
      };
    });
    window.addEventListener("popstate", function () {
      viewed(null);
    });
  }

  // --- Google Ads conversions, when the merchant chose them ----------------

  function loadConfig() {
    try {
      fetch(base + "/api/collect/config?k=" + encodeURIComponent(key), { credentials: "omit" })
        .then(function (r) {
          return r.ok ? r.json() : null;
        })
        .then(function (said) {
          if (!said || !said.tag) return;
          config = said;
          if (typeof window.gtag !== "function") {
            window.dataLayer = window.dataLayer || [];
            window.gtag = function () {
              window.dataLayer.push(arguments);
            };
            var tag = document.createElement("script");
            tag.async = true;
            tag.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(said.tag);
            document.head.appendChild(tag);
            window.gtag("js", new Date());
            window.gtag("config", said.tag);
          }
        })
        .catch(function () {});
    } catch (e) {
      /* no conversions to fire */
    }
  }
  function tellGoogle(sendTo) {
    if (sendTo && typeof window.gtag === "function") {
      window.gtag("event", "conversion", { send_to: sendTo });
    }
  }

  // --- leads: phone numbers and email addresses tapped ---------------------

  function onClick(event) {
    var link = event.target && event.target.closest && event.target.closest("a[href]");
    if (!link) return;
    var href = link.getAttribute("href") || "";
    var low = href.toLowerCase();
    if (low.indexOf("tel:") === 0) {
      send({ t: "lead", k: "call", url: location.href, h: href.slice(0, 300) });
      tellGoogle(config.call);
    } else if (low.indexOf("mailto:") === 0) {
      send({ t: "lead", k: "email", url: location.href, h: href.slice(0, 300) });
    }
  }

  // --- leads: forms sent ---------------------------------------------------

  var NEVER =
    /pass(word)?|pwd|card|cc-?num|cvv|cvc|csc|expir|iban|routing|account.?number|\bsin\b|\bssn\b/i;

  function labelOf(field, form) {
    var text = field.getAttribute("aria-label") || "";
    if (!text && field.id) {
      var label = form.querySelector(
        'label[for="' + (window.CSS && CSS.escape ? CSS.escape(field.id) : field.id) + '"]',
      );
      if (label) text = label.textContent || "";
    }
    if (!text) {
      var wrap = field.closest("label");
      if (wrap) text = wrap.textContent || "";
    }
    text = text || field.getAttribute("placeholder") || field.name || field.id || "";
    return text.replace(/\s+/g, " ").replace(/\*$/, "").trim().slice(0, 100);
  }

  function fieldsOf(form) {
    if (QUIET) return [];
    var out = [];
    var seen = {};
    for (var i = 0; i < form.elements.length && out.length < 25; i++) {
      var f = form.elements[i];
      var type = (f.type || "").toLowerCase();
      if (!f.name && !f.id) continue;
      if (/^(password|hidden|submit|button|reset|file|image)$/.test(type)) continue;
      if ((type === "checkbox" || type === "radio") && !f.checked) continue;
      var label = labelOf(f, form);
      if (NEVER.test(label) || NEVER.test(f.name || "") || NEVER.test(f.autocomplete || ""))
        continue;
      if (/^cc-/.test(f.autocomplete || "")) continue;
      var value =
        f.tagName === "SELECT" && f.selectedIndex >= 0 ? f.options[f.selectedIndex].text : f.value;
      value = String(value == null ? "" : value)
        .trim()
        .slice(0, 1000);
      if (!value) continue;
      var name = label || "Field";
      if (seen[name + value]) continue;
      seen[name + value] = true;
      out.push([name, value]);
    }
    return out;
  }

  function isSearchOrLogin(form) {
    if (form.getAttribute("data-ppcway") === "ignore") return true;
    if (form.getAttribute("role") === "search" || /search/i.test(form.className + " " + form.id))
      return true;
    if (form.querySelector('input[type="password"]')) return true;
    var inputs = form.querySelectorAll(
      "input:not([type=hidden]):not([type=submit]), textarea, select",
    );
    if (inputs.length === 1 && /^(s|q|search|query)$/i.test(inputs[0].name || "")) return true;
    return false;
  }

  function formName(form) {
    return (form.getAttribute("name") || form.id || form.getAttribute("aria-label") || "").slice(
      0,
      100,
    );
  }

  function report(form, fields) {
    send({ t: "lead", k: "form", url: location.href, n: formName(form), f: fields });
    tellGoogle(config.form);
  }

  /*
    Form tools that check what was typed after the button is pressed say when
    a form really went. For those, the lead waits for that word, so a form sent
    back for a missing field is not counted. Everything else counts on submit.
  */
  var waiting = [];
  function pluginOf(form) {
    var c = " " + form.className + " ";
    if (c.indexOf(" wpcf7-form ") >= 0) return "cf7";
    if (c.indexOf(" wpforms-form ") >= 0 || c.indexOf(" wpforms-ajax-form ") >= 0) return "wpforms";
    if (c.indexOf(" elementor-form ") >= 0) return "elementor";
    if (form.closest(".gform_wrapper")) return "gravity";
    return "";
  }
  function settle(match) {
    for (var i = waiting.length - 1; i >= 0; i--) {
      if (match(waiting[i])) {
        var held = waiting.splice(i, 1)[0];
        report(held.form, held.fields);
      }
    }
  }
  function watchFormTools() {
    document.addEventListener("wpcf7mailsent", function (event) {
      settle(function (held) {
        return (
          held.plugin === "cf7" &&
          (held.form === event.target ||
            held.form.contains(event.target) ||
            event.target.contains(held.form))
        );
      });
    });
    var $ = window.jQuery;
    if ($ && $.fn && $.fn.on) {
      $(document).on("wpformsAjaxSubmitSuccess", function (event) {
        settle(function (held) {
          return (
            held.plugin === "wpforms" &&
            (!event.target || event.target === held.form || $(event.target).is(held.form))
          );
        });
      });
      $(document).on("submit_success", function (event) {
        settle(function (held) {
          return (
            held.plugin === "elementor" &&
            (event.target === held.form || $.contains(held.form, event.target))
          );
        });
      });
      $(document).on("gform_confirmation_loaded", function () {
        settle(function (held) {
          return held.plugin === "gravity";
        });
      });
    }
  }

  function onSubmit(event) {
    var form = event.target;
    if (!form || form.tagName !== "FORM" || isSearchOrLogin(form)) return;
    var fields = fieldsOf(form);
    var plugin = pluginOf(form);
    var ajax =
      plugin === "cf7" ||
      plugin === "elementor" ||
      (plugin === "wpforms" && form.className.indexOf("wpforms-ajax-form") >= 0) ||
      (plugin === "gravity" &&
        (form.getAttribute("target") || "").indexOf("gform_ajax_frame") === 0);
    if (ajax) {
      // A form sent back for a missing field and then sent again is one lead:
      // the newer attempt replaces the one still waiting for its answer.
      waiting = waiting.filter(function (held) {
        return held.form !== form;
      });
      waiting.push({ form: form, fields: fields, plugin: plugin, at: Date.now() });
      // A success that never comes leaves nothing behind after a minute.
      setTimeout(function () {
        waiting = waiting.filter(function (held) {
          return Date.now() - held.at < 60000;
        });
      }, 61000);
      return;
    }
    report(form, fields);
  }

  // --- start, now or once the visitor agrees -------------------------------

  function start() {
    if (started) return;
    started = true;
    viewed(document.referrer);
    watchNavigation();
    watchFormTools();
    document.addEventListener("click", onClick, true);
    document.addEventListener("submit", onSubmit, true);
    loadConfig();
  }

  var queued = window.ppcway && window.ppcway.q ? window.ppcway.q : [];
  window.ppcway = function (command) {
    if (command === "consent") start();
  };
  var waitForConsent = me.getAttribute("data-consent") === "wait";
  for (var q = 0; q < queued.length; q++) window.ppcway.apply(null, queued[q]);
  if (!waitForConsent) start();
})();
