/* Service worker do GerEx Campo.

   Estrategia: cache primeiro, revalidando em segundo plano.

   A primeira versao buscava a rede antes do cache. Funcionava, mas em campo
   sem sinal a abertura ficava presa esperando o tempo de espera da rede antes
   de recorrer ao cache -- justamente onde o aplicativo precisa abrir na hora.
   Agora a pagina vem do cache imediatamente e, se houver rede, uma copia nova
   e baixada em silencio para a proxima abertura. */
const CACHE = "gerex-campo-v2";
const ARQUIVOS = ["./", "./index.html"];

self.addEventListener("install", ev => {
  ev.waitUntil(
    caches.open(CACHE).then(c => c.addAll(ARQUIVOS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", ev => {
  ev.waitUntil(
    caches.keys()
      // A origem do GitHub Pages e compartilhada com o GerLauNR10: apaga so
      // as versoes antigas do cache deste aplicativo.
      .then(chaves => Promise.all(chaves.filter(k => k.startsWith("gerex-campo-") && k !== CACHE)
                                        .map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", ev => {
  if (ev.request.method !== "GET") return;
  if (new URL(ev.request.url).origin !== location.origin) return;

  ev.respondWith(
    caches.match(ev.request).then(cacheado => {
      const daRede = fetch(ev.request).then(resp => {
        if (resp && resp.ok) {
          const copia = resp.clone();
          caches.open(CACHE).then(c => c.put(ev.request, copia)).catch(() => {});
        }
        return resp;
      }).catch(() => null);

      // offline: responde do cache na hora; a promessa da rede falha em silencio
      return cacheado || daRede.then(r => r || caches.match("./index.html"));
    })
  );
});
