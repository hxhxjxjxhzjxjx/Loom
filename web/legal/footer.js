/* Shared footer for all Lira static legal pages.
 * Edit ONLY this file to update the seller's requisites — the same
 * footer is included on every page via <script src="/legal/footer.js"
 * defer></script>. Placeholders look like <span class="lira-placeholder">
 * — the operator fills them in before going live. */
(function(){
  // ─── TODO: Replace these with your real legal-entity data ─────────────
  var SELLER = {
    name: "ИП Иванова Иванна Ивановна",           // ФИО / название ООО
    inn: "770000000000",                          // ИНН
    ogrn: "000000000000000",                       // ОГРН / ОГРНИП
    email: "support@lira.example.ru",              // e-mail поддержки
    address: "г. Москва, РФ",                      // юр.адрес (или регион)
    tg: "@lira_support_bot"                        // telegram поддержки
  };
  // ──────────────────────────────────────────────────────────────────────

  var html = (
    '<footer class="lira-footer">' +
      '<div class="links">' +
        '<a href="/">Главная</a>' +
        '<a href="/legal/privacy.html">Политика конфиденциальности</a>' +
        '<a href="/legal/offer.html">Договор-оферта</a>' +
        '<a href="/legal/about.html">О сервисе</a>' +
        '<a href="/legal/contacts.html">Контакты</a>' +
      '</div>' +
      '<div>' + escape(SELLER.name) + ' &middot; ИНН ' + escape(SELLER.inn) +
        ' &middot; ОГРН ' + escape(SELLER.ogrn) + '</div>' +
      '<div>Поддержка: <a href="mailto:' + escape(SELLER.email) + '">' +
        escape(SELLER.email) + '</a> &middot; Telegram: ' + escape(SELLER.tg) +
      '</div>' +
      '<div>&copy; ' + new Date().getFullYear() + ' Lira &middot; ' + escape(SELLER.address) + '</div>' +
    '</footer>'
  );

  function escape(s) {
    return String(s).replace(/[&<>"']/g, function(c){
      return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c];
    });
  }

  // Insert at end of <body>, after the <main>.
  document.addEventListener('DOMContentLoaded', function(){
    var holder = document.getElementById('lira-footer-slot');
    if (holder) holder.outerHTML = html;
    else document.body.insertAdjacentHTML('beforeend', html);

    // Expose for the page to fill in inline placeholders (the same
    // SELLER struct is the single source of truth).
    document.querySelectorAll('[data-seller]').forEach(function(el){
      var key = el.getAttribute('data-seller');
      if (SELLER[key] != null) el.textContent = SELLER[key];
    });
  });
})();
