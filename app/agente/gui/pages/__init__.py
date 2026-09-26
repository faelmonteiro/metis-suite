"""Mixins de `MetisMainWindow`, um por dominio de funcionalidade.

Compostos por heranca multipla na classe principal, entao continuam sendo os
mesmos metodos: nenhum corpo foi reescrito, nenhum sinal trocou de dono, e a
arvore de widgets sai identica.

Cada mixin vive no seu modulo e traz o `setup_*_ui` que monta a pagina
correspondente, mais os metodos que operam nela:

| mixin             | pagina          |
|-------------------|-----------------|
| `PlatformMixin`   | (transversal)   |
| `DashboardMixin`  | painel inicial  |
| `ChatMixin`       | chat + busca    |
| `OraclesMixin`    | oraculos        |
| `SessionsMixin`   | sessoes         |
| `AppearanceMixin` | aparencia       |
| `AiMixin`         | (transversal)   |
| `DialogsMixin`    | (transversal)   |

ATENCAO — os mixins nao sao independentes
-----------------------------------------
Eles compartilham estado de instancia por `self.<attr>`, e quem cria o
atributo raramente e quem o le. `PlatformMixin.toggle_or_focus` mexe em
`self.chat_layout`; `ChatMixin` le `self.current_service`; `AiMixin` le
`self.query_queue`, criado por `PlatformMixin`. Nenhum mixin sabe o
completo.

Isso e a estrutura original preservada — antes tudo estava em uma so
classe, e o acoplamento era o mesmo. Nao e um artefato da divisao. Mas
significa que mover um metodo entre dominios exige checar quem usa os
atributos que ele toca, e nao basta o metodo "caber" no dominio.

Nenhum mixin deve instanciar `MetisMainWindow` nem conhecer a classe
principal: quem chama `setup_*_ui` e `init_ui`, em
`agente/gui/main_window.py`.
"""
