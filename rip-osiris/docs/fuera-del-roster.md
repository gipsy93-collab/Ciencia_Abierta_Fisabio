# Personas del CRIS que no están en el portal (03-11-2026)

Del export de Fundanet (**1.105 filas**), **18 no aparecen en el roster** del portal de investigación. Dos son basura; **16 son personas reales**.

## Las 16

| Persona | ORCID | Obras en OpenAlex | Citas | Centro (Fundanet) |
|---|---|--:|--:|---|
| Lidia Remolí Sargües | `0000-0002-7919-0462` | **62** | 190 | H. Arnau de Vilanova |
| Mª José Soler Sempere | `0000-0002-6607-2037` | **46** | 170 | H. General de Elche |
| Carlos Valera Ribera | `0009-0007-3059-4347` | 16 | 36 | H. Dr. Peset |
| Isabel Fuster Martínez | `0000-0003-2957-5513` | 15 | 135 | Universitat de València |
| Esther Soler Climent | `0000-0002-8543-4865` | 15 | 30 | H. General de Elche |
| Emma Marín Payá | `0000-0003-3633-5550` | 10 | 16 | H. Arnau de Vilanova |
| Ana María Benedicto Elena | `0000-0001-9516-8815` | — | — | Universitat de València |
| Ester Francés Muñoz | `0009-0000-3744-9387` | — | — | H. Arnau de Vilanova |
| Joaquín Lacasa Molina | `0009-0001-4162-7390` | — | — | H. Dr. Peset |
| Enrique Vicente López Sánchez | `0000-0002-0850-2983` | — | — | H. Arnau de Vilanova |
| Ana Palau Gomar | `0009-0009-4024-3916` | — | — | H. Francesc de Borja |
| Luis Cejudo Berenguer | — | — | — | H. Virgen de los Lirios |
| Esther Cortés Zapatero | — | — | — | H. General de Elche |
| Juan Marín Montiel | — | — | — | H. Arnau de Vilanova |
| Ángeles Martínez Ferrer | — | — | — | H. Dr. Peset |
| José Vicente Visconti Gijón | — | — | — | DG Investigación Sanitaria |

**11 de 16 tienen ORCID (69 %), por encima del 61,5 % del roster.** Seis tienen producción indexada en OpenAlex.

## Las dos filas basura

- `PRUEBA` — un registro de prueba creado en el CRIS.
- `SEMICROL, S.L` — una empresa, no una persona.

Ninguna debería estar en un export de investigadores. Es un problema de calidad del CRIS, no nuestro.

## Qué significa

Hay dos explicaciones, y no son excluyentes:

1. **Altas posteriores al snapshot del portal.** El roster se cosechó en una fecha; el CRIS está vivo.
2. **Personas con contrato o colaboración que el portal no recoge.** El portal lista investigadores adscritos; el CRIS lista terceros con relación contractual.

El caso de **Lidia Remolí (62 obras)** y **Mª José Soler (46)** es el más llamativo: son investigadoras productivas que el portal no muestra. Si el portal es la fuente de verdad pública, ahí hay un fallo de visibilidad.

## Por qué no las he añadido

Añadirlas cambia el universo del proyecto: el roster pasaría de 1.087 a 1.103 y todas las coberturas se recalcularían. Y el esquema exige un `portal_id` que estas personas no tienen: habría que inventar uno (`fundanet:<n>`), lo que mezcla dos universos con reglas distintas.

**Decisión que corresponde a FISABIO, no a nosotros:** ¿el roster del proyecto es el portal o la unión de portal y CRIS?

- Si es **el portal**: estas 16 quedan fuera y se documentan.
- Si es **la unión**: hay que añadirlas con un `portal_id` sintético, marcarlas como `origen='fundanet'` y recalcular todas las coberturas.

## Recomendación

1. **Preguntar por las seis con producción** (Remolí, Soler Sempere, Valera, Fuster, Soler Climent, Marín Payá). Si siguen activas, deberían aparecer en el portal.
2. **Reportar las dos filas basura** al responsable del CRIS.
3. **No tocar el roster** hasta que haya respuesta.

Artefacto para revisión: `data/fuera_del_roster.csv`.
