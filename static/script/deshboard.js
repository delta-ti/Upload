  window.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("data_expiracao");
  const hoje = new Date().toISOString().split("T")[0]; // yyyy-mm-dd
  input.setAttribute("min", hoje);
});

  // Funções de loading
  function showLoading() {
    document.getElementById('loadingOverlay').style.display = 'flex';
  }
  function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
  }

  // Preenche lista de usuários e seleciona o logado
  async function preencherUsuarios() {
    showLoading();
    try {
      const resp = await fetch('/usuarios');
      const usuarios = await resp.json();
      const select = document.getElementById('usuarioSelect');
      select.innerHTML = '';
      let userLogado = Array.isArray(usuarios) ? usuarios[0] : (usuarios.users ? usuarios.users[0] : null);
      (Array.isArray(usuarios) ? usuarios : usuarios.users).forEach(user => {
        const opt = document.createElement('option');
        opt.value = user.auth_user_id;
        opt.textContent = user.nome || user.email || user.id;
        select.appendChild(opt);
      });
      // Seleciona o logado (primeiro da lista)
      if (userLogado) select.value = userLogado.auth_user_id;
    } catch {
      const select = document.getElementById('usuarioSelect');
      select.innerHTML = '<option value="">Erro ao buscar usuários</option>';
    }
    hideLoading();
    // Atualiza empresas e arquivos do usuário selecionado
    await atualizarEmpresasUsuario();
    listarArquivosUsuario();
  }

  // Atualiza empresas ao trocar usuário
  async function atualizarEmpresasUsuario() {
    const user_id = document.getElementById('usuarioSelect').value;
    const empresaRow = document.getElementById('empresaRow');
    const empresaSelect = document.getElementById('empresaSelect');
    empresaSelect.innerHTML = '<option value="">Selecione...</option>';
    empresaSelect.disabled = true;
    empresaRow.style.display = "none";
    if (!user_id) return;
    showLoading();
    try {
      const resp = await fetch(`/empresas_usuario/${user_id}`);
      const empresas = await resp.json();
      const aprovadas = (empresas || []).filter(emp =>
        emp.status_aprovacao && emp.status_aprovacao.toLowerCase() === 'aprovado'
        && emp.usuario_id === user_id
        && emp.empresa
      );
      if (aprovadas.length > 0) {
        aprovadas.forEach(emp => {
          let nome = (emp.empresa.nome_fantasia || emp.empresa.razao_social || emp.empresa_id);
          empresaSelect.innerHTML += `<option value="${emp.empresa_id}">${nome}</option>`;
        });
        empresaRow.style.display = "block";
        empresaSelect.disabled = false;
      } else {
        empresaRow.style.display = "none";
      }
    } catch (e) {
      empresaRow.style.display = "none";
    }
    hideLoading();
  }

  // Troca usuário: atualiza empresas e arquivos
  document.getElementById('usuarioSelect').addEventListener('change', async function () {
    await atualizarEmpresasUsuario();
    listarArquivosUsuario();
  });

  // Troca empresa: atualiza arquivos
  document.getElementById('empresaSelect').addEventListener('change', function() {
    showLoading();
    listarArquivosUsuario();
    hideLoading();
  });

  // Upload assíncrono
  document.getElementById('uploadForm').onsubmit = async function (e) {
    e.preventDefault();
    showLoading();
    const form = e.target;
    const data = new FormData(form);
    // Remove empresa_id se campo empresa não estiver visível
    if (document.getElementById('empresaRow').style.display === 'none') {
      data.delete('empresa_id');
    }
    document.getElementById('uploadResult').textContent = '';
    // Salva o usuário selecionado antes do reset
    const usuarioSelect = document.getElementById('usuarioSelect');
    const usuarioSelecionado = usuarioSelect.value;
    try {
      const resp = await fetch('/upload', { method: 'POST', body: data });
if (resp.ok) {
  const res = await resp.json();
  abrirModalUpload(res.url);

  form.reset();
  usuarioSelect.value = usuarioSelecionado;
  document.getElementById('empresaRow').style.display = 'none';
  listarArquivosUsuario();
}
     else {
        const erro = await resp.text();
        document.getElementById('uploadResult').textContent = erro;
      }
    } catch {
      document.getElementById('uploadResult').textContent = "Falha ao enviar.";
    }
    hideLoading();
  };

  // Listar arquivos do usuário selecionado, e só da empresa (se selecionada)
  async function listarArquivosUsuario() {
    showLoading();
    const select = document.getElementById('usuarioSelect');
    const user_id = select.value;
    const empresaSelect = document.getElementById('empresaSelect');
    const empresaRow = document.getElementById('empresaRow');
    const empresa_id = (empresaRow.style.display !== 'none' && empresaSelect.value) ? empresaSelect.value : null;
    const div = document.getElementById('arquivosLista');
    if (!user_id) {
      div.innerHTML = "<em>Selecione um usuário.</em>";
      hideLoading();
      return;
    }

    // Se empresaRow visível e não selecionou empresa, mostra só arquivos sem vínculo
    if (empresaRow.style.display !== 'none' && !empresa_id) {
      // Busca apenas arquivos sem empresa vinculada
      let url = `/arquivos?user_id=${encodeURIComponent(user_id)}&empresa_id=SEM_VINCULO`;
      await fetchAndRenderArquivos(url, div);
      hideLoading();
      return;
    }

    let url = `/arquivos?user_id=${encodeURIComponent(user_id)}`;
    if (empresa_id) url += `&empresa_id=${encodeURIComponent(empresa_id)}`;
    await fetchAndRenderArquivos(url, div);
    hideLoading();
  }

  // Função auxiliar para buscar e renderizar arquivos
  async function fetchAndRenderArquivos(url, div) {
    div.innerHTML = "Carregando...";
    try {
      const resp = await fetch(url);
      const arquivos = await resp.json();
      if (!Array.isArray(arquivos) || arquivos.length === 0) {
        div.innerHTML = "<em>Nenhum arquivo cadastrado para este filtro.</em>";
        return;
      }
      let html = "";
      arquivos.forEach(arq => {
        html += `
          <div class="lista-item" style="position:relative;">
            <div class="lista-icon">
              ${
                arq.tipo && arq.tipo.startsWith('image')
                  ? `<img src="${arq.url}" alt="Imagem ${arq.id}" style="max-width:54px;max-height:54px;border-radius:8px;border:1px solid #e0e3ec;background:#fff;">`
                  : `<span class="pdf-icon" style="color:#5176f3;font-size:2.3em;">&#128462;</span>`
              }
            </div>
            <div class="lista-info" style="flex:1;">
              <span class="label" style="color:#888;">Nome:</span> <b>${arq.nome}</b><br>
              <span class="label" style="color:#888;">Tipo:</span> ${arq.tipo || '-'}<br>
              ${
                arq.data_expiracao
                  ? (() => {
                      const expDate = new Date(arq.data_expiracao + "T12:00:00");
                      const hoje = new Date();
                      hoje.setHours(0, 0, 0, 0);
                      expDate.setHours(0, 0, 0, 0);
                      const diffDias = Math.floor((expDate - hoje) / (1000 * 60 * 60 * 24));

                      let cor = "#222"; // padrão
                      if (diffDias < 0) cor = "#c52222";            // vencido
                      else if (diffDias <= 4) cor = "#d97706";      // até 4 dias
                      else cor = "#15803d";                         // acima de 4 dias

                      return `
                        <span class="label" style="color:#888;">Expira em:</span>
                        <b style="color: ${cor};">${expDate.toLocaleDateString()}</b>
                      `;
                    })()
                  : ''
              }
            </div>
            <div class="botoes-arquivo">
              <a href="${arq.url}" download target="_blank" class="download-btn">
                <span style="font-size:1.15em;vertical-align:-2px;">&#128229;</span> Download
              </a>
              <button class="danger" onclick="deletarArquivo('${arq.id}', this)">Excluir</button>
            </div>
          </div>
        `;
      });
      div.innerHTML = html;
    } catch {
      div.innerHTML = "<span class='error'>Falha ao buscar arquivos.</span>";
    }
  }

 // PATCH para soft delete
let pendingDelete = { id: null, button: null };

function deletarArquivo(arquivo_id, btn) {
  pendingDelete = { id: arquivo_id, button: btn };
  document.getElementById("modalConfirm").style.display = "flex";
}

async function confirmarExclusao() {
  const { id, button } = pendingDelete;
  if (!id || !button) return;

  document.getElementById("modalConfirm").style.display = "none";
  button.disabled = true;
  button.innerHTML = `<span style="color:var(--primary-dark);">⌛</span> Excluindo...`;
  showLoading();

  try {
    const resp = await fetch(`/arquivo/${id}`, {
      method: "PATCH",
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ativo: false, status: "inativo" })
    });

    const res = await resp.json();

    if (resp.ok) {
      button.closest('.lista-item')?.remove();
      abrirModal(); // Mostra o modal de sucesso
    } else {
      exibirMensagemErro("Erro ao excluir: " + (res.erro || "Desconhecido"));
      button.disabled = false;
      button.textContent = "Excluir";
    }

  } catch (e) {
    exibirMensagemErro("Erro inesperado ao excluir.");
    button.disabled = false;
    button.textContent = "Excluir";
  }

  hideLoading();
}

function cancelarExclusao() {
  document.getElementById("modalConfirm").style.display = "none";
  pendingDelete = { id: null, button: null };
}

// Exibe modal de sucesso e fecha após 2 segundos
function abrirModal() {
  const modal = document.getElementById("modalSucesso");
  modal.style.display = "flex";
  setTimeout(() => {
    fecharModal();
  }, 2000);
}

function fecharModal() {
  document.getElementById("modalSucesso").style.display = "none";
}

// Cria alerta inline de erro com estilo
function exibirMensagemErro(msg) {
  const div = document.createElement("div");
  div.textContent = msg;
  div.style.cssText = `
    background: #fdecea;
    color: #b91c1c;
    border: 1px solid #fca5a5;
    padding: 10px 16px;
    margin: 14px 0;
    border-radius: var(--radius);
    font-weight: 600;
    box-shadow: 0 1px 6px #0000000f;
  `;
  document.querySelector(".main-content")?.prepend(div);
  setTimeout(() => div.remove(), 4000);
}
function abrirModalUpload(urlArquivo) {
  const modal = document.getElementById("modalUpload");
  const link = document.getElementById("modalUploadLink");
  modal.style.display = "flex";
  link.href = urlArquivo;
  link.textContent = "Abrir arquivo";
  setTimeout(() => {
    fecharModalUpload();
  }, 3000);
}

function fecharModalUpload() {
  document.getElementById("modalUpload").style.display = "none";
}

// Inicialização
preencherUsuarios();
