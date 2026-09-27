// Fallback de SPA do CapiWatt (issue #107), CloudFront Function no
// viewer-request do comportamento padrao (so o frontend; /v1/* nao passa aqui).
// Caminho cujo ultimo segmento nao termina em extensao de arquivo vira
// /index.html, e o roteador do app resolve a rota. Extensao = ponto seguido de
// letra e ate 9 alfanumericos: ids de processo SEI tem ponto
// (48500.001234%2F2024-11) e continuam sendo rotas do app.
var FILE_EXTENSION = /\.[A-Za-z][A-Za-z0-9]{0,9}$/;

function handler(event) {
  var request = event.request;
  var last = request.uri.substring(request.uri.lastIndexOf("/") + 1);
  if (!FILE_EXTENSION.test(last)) {
    request.uri = "/index.html";
  }
  return request;
}
