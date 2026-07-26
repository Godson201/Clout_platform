import { useQuery } from "@tanstack/react-query";

export interface RwandaLocationTree {
  provinces: string[];
  districtsByProvince: Map<string, string[]>;
  sectorsByDistrict: Map<string, string[]>;
  cellsBySector: Map<string, string[]>;
  villagesByCell: Map<string, string[]>;
}

function districtKey(province: string) {
  return province;
}
function sectorKey(province: string, district: string) {
  return `${province}::${district}`;
}
function cellKey(province: string, district: string, sector: string) {
  return `${province}::${district}::${sector}`;
}
function villageKey(province: string, district: string, sector: string, cell: string) {
  return `${province}::${district}::${sector}::${cell}`;
}

export const rwandaLocationKeys = { districtKey, sectorKey, cellKey, villageKey };

function addToMap(map: Map<string, Set<string>>, key: string, value: string) {
  let set = map.get(key);
  if (!set) {
    set = new Set();
    map.set(key, set);
  }
  set.add(value);
}

function finalize(map: Map<string, Set<string>>): Map<string, string[]> {
  const result = new Map<string, string[]>();
  for (const [key, set] of map) {
    result.set(key, Array.from(set).sort());
  }
  return result;
}

// The file is plain "province,district,sector,cell,village" rows with no
// embedded commas or quoting (verified against the source data), so a simple
// split is safe and much cheaper than pulling in a CSV parsing library for one file.
function parseCsv(text: string): RwandaLocationTree {
  const provinces = new Set<string>();
  const districtsByProvince = new Map<string, Set<string>>();
  const sectorsByDistrict = new Map<string, Set<string>>();
  const cellsBySector = new Map<string, Set<string>>();
  const villagesByCell = new Map<string, Set<string>>();

  const lines = text.split("\n");
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    const [, province, district, sector, cell, village] = line.split(",");
    if (!province || !district) continue;

    provinces.add(province);
    addToMap(districtsByProvince, districtKey(province), district);
    if (sector) addToMap(sectorsByDistrict, sectorKey(province, district), sector);
    if (sector && cell) addToMap(cellsBySector, cellKey(province, district, sector), cell);
    if (sector && cell && village) addToMap(villagesByCell, villageKey(province, district, sector, cell), village);
  }

  return {
    provinces: Array.from(provinces).sort(),
    districtsByProvince: finalize(districtsByProvince),
    sectorsByDistrict: finalize(sectorsByDistrict),
    cellsBySector: finalize(cellsBySector),
    villagesByCell: finalize(villagesByCell),
  };
}

let loadPromise: Promise<RwandaLocationTree> | null = null;

function loadRwandaLocations(): Promise<RwandaLocationTree> {
  loadPromise ??= fetch("/rwandasdata.csv")
    .then((res) => res.text())
    .then(parseCsv);
  return loadPromise;
}

export function useRwandaLocations() {
  return useQuery({
    queryKey: ["rwanda-locations"],
    queryFn: loadRwandaLocations,
    staleTime: Infinity,
    gcTime: Infinity,
  });
}
