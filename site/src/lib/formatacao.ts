/** Formatacao em pt-PT. Sem dependencias, para poder ser usada tanto na build
 * como nas ilhas de interatividade do browser.
 *
 * As datas nunca passam por `Date`: as anteriores a 1582 estao no calendario
 * juliano e o `Date` do JavaScript so conhece o gregoriano proleptico. Aqui
 * trata-se a data como o que ela e nos ficheiros, tres numeros. */

import type {
  Calendario,
  EntradaIndice,
  SistemaHora,
  Territorio,
  TipoEclipse,
  TipoLocal,
} from "./tipos";

const MESES = [
  "janeiro",
  "fevereiro",
  "março",
  "abril",
  "maio",
  "junho",
  "julho",
  "agosto",
  "setembro",
  "outubro",
  "novembro",
  "dezembro",
];

export function partesData(iso: string): [number, number, number] {
  const [ano, mes, dia] = iso.split("-").map(Number);
  return [ano!, mes!, dia!];
}

export function anoDe(iso: string): number {
  return partesData(iso)[0];
}

export function seculoDe(iso: string): number {
  return Math.floor((anoDe(iso) - 1) / 100) + 1;
}

/** "28 de maio de 1900" */
export function dataPorExtenso(iso: string): string {
  const [ano, mes, dia] = partesData(iso);
  return `${dia} de ${MESES[mes - 1]} de ${ano}`;
}

/** "28/05/1900" */
export function dataCurta(iso: string): string {
  const [ano, mes, dia] = partesData(iso);
  return `${pad(dia)}/${pad(mes)}/${ano}`;
}

/** A data como se via em Portugal a epoca, com a do outro calendario a seguir
 * quando os dois diferem. */
export function dataVigente(e: {
  data_gregoriana: string;
  data_juliana: string | null;
  calendario_vigente_pt: Calendario;
}): { principal: string; alternativa: string | null; calendario: Calendario } {
  if (e.calendario_vigente_pt === "juliano" && e.data_juliana) {
    return {
      principal: e.data_juliana,
      alternativa: e.data_gregoriana,
      calendario: "juliano",
    };
  }
  return {
    principal: e.data_gregoriana,
    alternativa: null,
    calendario: "gregoriano",
  };
}

export function numero(valor: number, casas = 2): string {
  return new Intl.NumberFormat("pt-PT", {
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  }).format(valor);
}

/** Magnitudes e obscuracoes: quatro casas sao ruido, duas escondem o 1,00 de um
 * total rasante. Tres e o compromisso. */
export function magnitude(valor: number): string {
  return numero(valor, 3);
}

export function percentagem(fraccao: number, casas = 1): string {
  return `${numero(fraccao * 100, casas)} %`;
}

export function graus(valor: number, casas = 1): string {
  return `${numero(valor, casas)}°`;
}

/** "15:28" */
export function horaCurta(hora: string): string {
  return hora.slice(0, 5);
}

/** "1 min 29 s", "89,3 s" abaixo do minuto. */
export function duracao(segundos: number): string {
  if (segundos < 60) return `${numero(segundos, 1)} s`;
  const minutos = Math.floor(segundos / 60);
  const resto = Math.round(segundos - minutos * 60);
  return resto === 0 ? `${minutos} min` : `${minutos} min ${resto} s`;
}

/** "40,862° N, 8,617° O". Em portugues o ponto cardeal e Oeste, nao West. */
export function coordenadas(lat: number, lon: number): string {
  const latitude = `${numero(Math.abs(lat), 3)}° ${lat >= 0 ? "N" : "S"}`;
  const longitude = `${numero(Math.abs(lon), 3)}° ${lon >= 0 ? "E" : "O"}`;
  return `${latitude}, ${longitude}`;
}

export const NOMES_TERRITORIO: Record<Territorio, string> = {
  continente: "Continente",
  acores: "Açores",
  madeira: "Madeira",
};

export const NOMES_TIPO: Record<TipoEclipse, string> = {
  total: "Total",
  anular: "Anular",
  hibrido: "Híbrido",
  parcial: "Parcial",
};

export const NOMES_TIPO_LOCAL: Record<TipoLocal, string> = {
  ...NOMES_TIPO,
  nenhum: "Nenhum",
};

/** Como rotular a hora mostrada. Antes de 1912 nao havia hora legal em
 * Portugal: cada terra regia-se pelo seu meio-dia, e e isso que o pipeline
 * calcula. */
export function rotuloSistemaHora(
  sistema: SistemaHora,
  designacaoFuso: string | null,
): string {
  if (sistema === "hora_legal") {
    return designacaoFuso ? `hora legal (${designacaoFuso})` : "hora legal";
  }
  return "hora solar média local";
}

/** Titulo curto de um eclipse, para listas e navegacao. */
export function titulo(e: EntradaIndice): string {
  const { principal } = dataVigente(e);
  return `Eclipse ${NOMES_TIPO[e.tipo].toLowerCase()} de ${dataPorExtenso(principal)}`;
}

function pad(valor: number): string {
  return String(valor).padStart(2, "0");
}
