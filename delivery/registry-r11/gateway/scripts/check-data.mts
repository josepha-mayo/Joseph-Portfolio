import { loadData } from "../netlify/functions/_shared/data.mts";
import { validateData } from "../netlify/functions/_shared/registry.mts";

const data = await loadData();
const checked = validateData(data);
console.log(JSON.stringify({ status: "valid", manifest_digest: data.routing.manifestDigest,
  layers: checked.manifest.layers.length, repository: data.routing.repository }));
