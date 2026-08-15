/** Datas e horas: calendario juliano ou gregoriano, e hora local em Portugal.
 *
 * Porto para TypeScript de `pipeline/calendario.py`, para o calculo ao vivo no
 * mapa poder datar os seus proprios resultados sem os ir buscar ao servidor.
 * As duas armadilhas historicas sao as mesmas:
 *
 * Calendario. O canon usa o juliano ate 1582 e o gregoriano a partir dai.
 * Portugal adoptou o gregoriano na data da bula, saltando de 4 para 15 de
 * outubro de 1582. As datas nunca passam pelo `Date` do JavaScript, que so
 * conhece o gregoriano proleptico: convertem-se do dia juliano a mao, com o
 * algoritmo do Meeus, capitulo 7.
 *
 * Hora. A hora legal so existe em Portugal desde 1912. Antes disso a unica hora
 * com significado num ponto e a hora solar media do seu meridiano. A partir de
 * 1912 usa-se a base de fusos do sistema, atraves do `Intl`, que ja trata da
 * hora de verao historica e do periodo de 1992 a 1996 em que o continente
 * esteve na hora da Europa Central. */

import type { Calendario, SistemaHora, Territorio } from "./tipos";

/** Portugal passou de 4 de outubro (juliano) a 15 de outubro de 1582. */
export const JD_ADOPCAO_GREGORIANO_PT = 2299160.5;

/** A partir daqui ha hora legal em Portugal e a base de fusos e fiavel. */
export const ANO_PRIMEIRA_HORA_LEGAL = 1912;

const FUSOS: Record<Territorio, string> = {
  continente: "Europe/Lisbon",
  acores: "Atlantic/Azores",
  madeira: "Atlantic/Madeira",
};

export interface DataCivil {
  ano: number;
  mes: number;
  dia: number;
  hora: number;
  minuto: number;
  segundo: number;
}

/** Converte um dia juliano na data civil do calendario pedido.
 *
 * O calendario e escolhido pelo chamador em vez de inferido, porque a mesma
 * data pode ter de ser apresentada nos dois. Meeus, capitulo 7. */
export function jdParaCivil(jd: number, gregoriano: boolean): DataCivil {
  const deslocado = jd + 0.5;
  const z = Math.floor(deslocado);
  const f = deslocado - z;

  let a = z;
  if (gregoriano) {
    const alfa = Math.floor((z - 1867216.25) / 36524.25);
    a = z + 1 + alfa - Math.floor(alfa / 4);
  }

  const b = a + 1524;
  const c = Math.floor((b - 122.1) / 365.25);
  const d = Math.floor(365.25 * c);
  const e = Math.floor((b - d) / 30.6001);

  const diaFraccionario = b - d - Math.floor(30.6001 * e) + f;
  const dia = Math.floor(diaFraccionario);
  const mes = e < 14 ? e - 1 : e - 13;
  const ano = mes > 2 ? c - 4716 : c - 4715;

  const restoHoras = (diaFraccionario - dia) * 24.0;
  const hora = Math.floor(restoHoras);
  const restoMinutos = (restoHoras - hora) * 60.0;
  const minuto = Math.floor(restoMinutos);
  const segundo = (restoMinutos - minuto) * 60.0;

  return { ano, mes, dia, hora, minuto, segundo };
}

/** Inverso de `jdParaCivil`. */
export function civilParaJd(
  ano: number,
  mes: number,
  dia: number,
  gregoriano: boolean,
): number {
  let a = ano;
  let m = mes;
  if (m <= 2) {
    a -= 1;
    m += 12;
  }
  const b = gregoriano
    ? 2 - Math.floor(a / 100) + Math.floor(Math.floor(a / 100) / 4)
    : 0;
  return (
    Math.floor(365.25 * (a + 4716)) +
    Math.floor(30.6001 * (m + 1)) +
    dia +
    b -
    1524.5
  );
}

/** "1900-05-28" */
export function isoData(c: DataCivil): string {
  return `${String(c.ano).padStart(4, "0")}-${dois(c.mes)}-${dois(c.dia)}`;
}

/** "15:27:56". Os segundos sao truncados, como no pipeline. */
export function isoHora(c: DataCivil): string {
  return `${dois(c.hora)}:${dois(c.minuto)}:${dois(Math.floor(c.segundo))}`;
}

/** Qual dos calendarios estava em vigor em Portugal nesse dia juliano. */
export function calendarioVigente(jd: number): Calendario {
  return jd >= JD_ADOPCAO_GREGORIANO_PT ? "gregoriano" : "juliano";
}

/** Dia juliano em UT de um instante `t` dos elementos besselianos.
 *
 * `jd_t0_td` vem na ficha do eclipse, calculado pelo pipeline a partir da data
 * e da hora do maximo publicadas pelo canon. E o unico numero que liga o tempo
 * dos polinomios ao calendario, e vem pronto para o browser nao ter de repetir
 * essa aritmetica nem os cuidados que ela exige. */
export function jdUtDeT(
  eclipse: { jd_t0_td: number; delta_t_s: number },
  t: number,
): number {
  return eclipse.jd_t0_td + t / 24.0 - eclipse.delta_t_s / 86400.0;
}

export interface HoraLocal {
  data: string;
  hora: string;
  sistema: SistemaHora;
  desvio_utc_h: number;
}

/** Hora local num ponto, no sistema que fazia sentido a data.
 *
 * Devolve a data e a hora ja convertidas, mais a etiqueta do sistema usado,
 * para a interface poder dizer ao leitor o que esta a ver. */
export function horaLocal(
  jdUt: number,
  lonGraus: number,
  territorio: Territorio,
): HoraLocal {
  const civilUt = jdParaCivil(jdUt, true);

  if (civilUt.ano >= ANO_PRIMEIRA_HORA_LEGAL) {
    // Os segundos truncam-se antes da conversao, como no pipeline, para os dois
    // lados arredondarem no mesmo sitio.
    const instante = instanteUtc(civilUt);
    const local = noFuso(instante, FUSOS[territorio]);
    return {
      data: isoData(local),
      hora: isoHora(local),
      sistema: "hora_legal",
      desvio_utc_h: (instanteUtc(local).getTime() - instante.getTime()) / 3600000,
    };
  }

  // Hora solar media do meridiano do ponto: quatro minutos por grau.
  const jdLocal = jdUt + lonGraus / 360.0;
  const civilLocal = jdParaCivil(jdLocal, true);
  const civilJuliano = jdParaCivil(jdLocal, false);
  const juliano = calendarioVigente(jdUt) === "juliano";

  return {
    data: isoData(juliano ? civilJuliano : civilLocal),
    hora: isoHora(civilLocal),
    sistema: "hora_solar_media_local",
    desvio_utc_h: lonGraus / 15.0,
  };
}

/** Desvio em relacao ao UTC, para etiquetar a hora mostrada: "UTC+01:00".
 *
 * A hora legal aparece com o desvio em vez da sigla do fuso. As siglas
 * historicas nao sao as mesmas em todas as bases de dados de fusos, e o desvio
 * diz o mesmo sem ambiguidade. */
export function desvioUtc(horas: number): string {
  const sinal = horas < 0 ? "-" : "+";
  const total = Math.round(Math.abs(horas) * 60);
  return `UTC${sinal}${dois(Math.floor(total / 60))}:${dois(total % 60)}`;
}

/** Um instante UTC a partir de componentes civis gregorianas.
 *
 * `Date.UTC` interpreta os anos de dois digitos como do seculo XX, por isso o
 * ano e reposto a seguir. Sem isso, um eclipse do ano 99 iria parar a 1999. */
function instanteUtc(c: DataCivil): Date {
  const data = new Date(
    Date.UTC(2000, c.mes - 1, c.dia, c.hora, c.minuto, Math.floor(c.segundo)),
  );
  data.setUTCFullYear(c.ano);
  return data;
}

const formatadores = new Map<string, Intl.DateTimeFormat>();

/** As componentes civis de um instante, num fuso horario. */
function noFuso(instante: Date, fuso: string): DataCivil {
  let formatador = formatadores.get(fuso);
  if (!formatador) {
    formatador = new Intl.DateTimeFormat("en-GB", {
      timeZone: fuso,
      hourCycle: "h23",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
    formatadores.set(fuso, formatador);
  }

  const partes: Record<string, number> = {};
  for (const parte of formatador.formatToParts(instante)) {
    if (parte.type !== "literal") partes[parte.type] = Number(parte.value);
  }
  return {
    ano: partes.year!,
    mes: partes.month!,
    dia: partes.day!,
    hora: partes.hour!,
    minuto: partes.minute!,
    segundo: partes.second!,
  };
}

function dois(valor: number): string {
  return String(valor).padStart(2, "0");
}
