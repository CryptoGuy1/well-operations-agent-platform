// The author and the data attributions of NOTICE, on every page.

import { Author } from "./Author";

export function Footer() {
  return (
    <footer className="footer">
      <Author className="author--footer" />
      <h2 className="visually-hidden">Data attribution</h2>
      <p>
        Contains Volve field data from{" "}
        <a href="https://www.equinor.com/energy/volve-data-sharing">Equinor ASA</a> and the Volve
        licence partners, under the Equinor Open Data Licence. The data must not be sold, alone or
        as part of another product.
      </p>
      <p>
        Contains data under the Norwegian licence for Open Government data (
        <a href="https://data.norge.no/nlod/en/2.0">NLOD 2.0</a>) distributed by the Norwegian
        Offshore Directorate (<a href="https://factpages.sodir.no/">Sodir FactPages</a>).
      </p>
      <p>
        Source code under the Apache License 2.0. Data shown here is derived from these sources and
        remains under their licences; see NOTICE in the repository.
      </p>
    </footer>
  );
}
