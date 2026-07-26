"use client";

import { useMemo } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { rwandaLocationKeys, useRwandaLocations } from "@/lib/rwanda-locations";

export interface RwandaLocationValue {
  province: string;
  location: string;
  admin_sector: string;
  admin_cell: string;
  admin_village: string;
  address_detail: string;
}

export function emptyRwandaLocation(): RwandaLocationValue {
  return { province: "", location: "", admin_sector: "", admin_cell: "", admin_village: "", address_detail: "" };
}

interface RwandaLocationPickerProps {
  value: Partial<RwandaLocationValue>;
  onChange: (patch: Partial<RwandaLocationValue>) => void;
}

export function RwandaLocationPicker({ value, onChange }: RwandaLocationPickerProps) {
  const { data: tree, isLoading } = useRwandaLocations();

  const districts = useMemo(() => {
    if (!tree || !value.province) return [];
    return tree.districtsByProvince.get(rwandaLocationKeys.districtKey(value.province)) ?? [];
  }, [tree, value.province]);

  const sectors = useMemo(() => {
    if (!tree || !value.province || !value.location) return [];
    return tree.sectorsByDistrict.get(rwandaLocationKeys.sectorKey(value.province, value.location)) ?? [];
  }, [tree, value.province, value.location]);

  const cells = useMemo(() => {
    if (!tree || !value.province || !value.location || !value.admin_sector) return [];
    return tree.cellsBySector.get(rwandaLocationKeys.cellKey(value.province, value.location, value.admin_sector)) ?? [];
  }, [tree, value.province, value.location, value.admin_sector]);

  const villages = useMemo(() => {
    if (!tree || !value.province || !value.location || !value.admin_sector || !value.admin_cell) return [];
    return (
      tree.villagesByCell.get(
        rwandaLocationKeys.villageKey(value.province, value.location, value.admin_sector, value.admin_cell),
      ) ?? []
    );
  }, [tree, value.province, value.location, value.admin_sector, value.admin_cell]);

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-2">
          <Label>Province</Label>
          <Select
            value={value.province ?? ""}
            onValueChange={(v) =>
              onChange({ province: v ?? "", location: "", admin_sector: "", admin_cell: "", admin_village: "" })
            }
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder={isLoading ? "Loading..." : "Select province"} />
            </SelectTrigger>
            <SelectContent>
              {tree?.provinces.map((p) => (
                <SelectItem key={p} value={p}>
                  {p}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>District</Label>
          <Select
            value={value.location ?? ""}
            onValueChange={(v) => onChange({ location: v ?? "", admin_sector: "", admin_cell: "", admin_village: "" })}
            disabled={!value.province}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select district" />
            </SelectTrigger>
            <SelectContent>
              {districts.map((d) => (
                <SelectItem key={d} value={d}>
                  {d}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="space-y-2">
          <Label className="text-muted-foreground">Sector (optional)</Label>
          <Select
            value={value.admin_sector ?? ""}
            onValueChange={(v) => onChange({ admin_sector: v ?? "", admin_cell: "", admin_village: "" })}
            disabled={!value.location}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Sector" />
            </SelectTrigger>
            <SelectContent>
              {sectors.map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label className="text-muted-foreground">Cell (optional)</Label>
          <Select
            value={value.admin_cell ?? ""}
            onValueChange={(v) => onChange({ admin_cell: v ?? "", admin_village: "" })}
            disabled={!value.admin_sector}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Cell" />
            </SelectTrigger>
            <SelectContent>
              {cells.map((c) => (
                <SelectItem key={c} value={c}>
                  {c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label className="text-muted-foreground">Village (optional)</Label>
          <Select
            value={value.admin_village ?? ""}
            onValueChange={(v) => onChange({ admin_village: v ?? "" })}
            disabled={!value.admin_cell}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Village" />
            </SelectTrigger>
            <SelectContent>
              {villages.map((v) => (
                <SelectItem key={v} value={v}>
                  {v}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-2">
        <Label className="text-muted-foreground">Address details (optional)</Label>
        <Input
          value={value.address_detail ?? ""}
          onChange={(e) => onChange({ address_detail: e.target.value })}
          placeholder="Street, landmark, or house number — helps people find you on the map"
        />
      </div>
    </div>
  );
}
