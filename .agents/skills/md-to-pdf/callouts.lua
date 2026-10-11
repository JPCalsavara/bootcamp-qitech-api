-- Pandoc Lua Filter: Callouts e Ajuste Automático de Largura de Tabelas
-- Garante que tabelas nunca estourem as margens da página no LaTeX

function Div(el)
  local callout_classes = {
    calloutnote = "calloutnote",
    calloutimportant = "calloutimportant",
    calloutwarning = "calloutwarning",
    callouttip = "callouttip"
  }
  for cls, env in pairs(callout_classes) do
    if el.classes:includes(cls) then
      table.insert(el.content, 1, pandoc.RawBlock("latex", "\\begin{" .. env .. "}"))
      table.insert(el.content, pandoc.RawBlock("latex", "\\end{" .. env .. "}"))
      return el.content
    end
  end
end

function Table(el)
  local num_cols = #el.colspecs
  if num_cols > 0 then
    local new_specs = {}
    if num_cols == 5 then
      -- Tabela padrão de Rotas da RFC: Método, Caminho, O que faz, Entrada, Saídas
      new_specs = {
        {el.colspecs[1][1], 0.09}, -- Método
        {el.colspecs[2][1], 0.30}, -- Caminho
        {el.colspecs[3][1], 0.23}, -- O que faz
        {el.colspecs[4][1], 0.15}, -- Entrada
        {el.colspecs[5][1], 0.23}  -- Saídas
      }
    elseif num_cols == 2 then
      new_specs = {
        {el.colspecs[1][1], 0.25},
        {el.colspecs[2][1], 0.75}
      }
    elseif num_cols == 3 then
      new_specs = {
        {el.colspecs[1][1], 0.22},
        {el.colspecs[2][1], 0.38},
        {el.colspecs[3][1], 0.40}
      }
    elseif num_cols == 4 then
      new_specs = {
        {el.colspecs[1][1], 0.14},
        {el.colspecs[2][1], 0.28},
        {el.colspecs[3][1], 0.28},
        {el.colspecs[4][1], 0.30}
      }
    else
      for i, spec in ipairs(el.colspecs) do
        table.insert(new_specs, {spec[1], 1.0 / num_cols})
      end
    end
    el.colspecs = new_specs
    return el
  end
end

-- Helper para escapar caracteres especiais de LaTeX e permitir quebra limpa
local function format_breakable_code(text)
  local s = text
  -- Escapar caracteres especiais de LaTeX
  s = s:gsub("\\", "\\textbackslash{}")
  s = s:gsub("([{}%%$&_#])", "\\%1")
  s = s:gsub("%^", "\\textasciicircum{}")
  s = s:gsub("~", "\\textasciitilde{}")

  -- Adiciona \protect\allowbreak após barras intermediárias (mantendo / inicial colada)
  local head, rest = s:match("^(/?)(.*)$")
  if rest and #rest > 0 then
    rest = rest:gsub("/", "/\\protect\\allowbreak ")
    s = head .. rest
  end

  -- Adiciona quebra após sublinhados e hífens
  s = s:gsub("(\\_)", "%1\\protect\\allowbreak ")
  s = s:gsub("(%-)", "%1\\protect\\allowbreak ")

  return "\\texttt{" .. s .. "}"
end

function Code(el)
  -- Permite quebra em códigos inline que representam rotas, identificadores com underscore ou hífens longos
  if el.text:find("/") or (el.text:find("_") and #el.text > 10) or (el.text:find("%-") and #el.text > 12) then
    return pandoc.RawInline("latex", format_breakable_code(el.text))
  end
end

function Str(el)
  -- Quebra em caminhos de API que aparecem como texto puro (ex: /customers/{key}/...)
  if el.text:match("^/[%a%d_{}%-]+/") then
    local head, rest = el.text:match("^(/?)(.*)$")
    local pieces = {}
    for part in rest:gmatch("[^/]+") do
      table.insert(pieces, part)
    end
    local inlines = {}
    table.insert(inlines, pandoc.Str(head))
    for i, p in ipairs(pieces) do
      table.insert(inlines, pandoc.Str(p))
      if i < #pieces or rest:sub(-1) == "/" then
        table.insert(inlines, pandoc.Str("/"))
        table.insert(inlines, pandoc.RawInline("latex", "\\protect\\allowbreak "))
      end
    end
    return inlines
  end
end
