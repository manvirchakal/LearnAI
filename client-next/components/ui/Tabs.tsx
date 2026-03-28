"use client";
import { Tabs as MuiTabs, Tab, TabsProps, Box } from "@mui/material";
import { ReactNode } from "react";

export interface TabItem {
  label: string;
  value: string;
  icon?: ReactNode;
}

interface Props extends Omit<TabsProps, "onChange"> {
  items: TabItem[];
  value: string;
  onChange: (value: string) => void;
}

export default function Tabs({ items, value, onChange, sx, ...props }: Props) {
  return (
    <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
      <MuiTabs
        value={value}
        onChange={(_, v) => onChange(v)}
        sx={{ minHeight: 44, ...sx }}
        {...props}
      >
        {items.map((item) => (
          <Tab
            key={item.value}
            label={item.label}
            value={item.value}
            icon={item.icon as any}
            iconPosition="start"
            sx={{ minHeight: 44, textTransform: "none", fontWeight: 500, fontSize: 13 }}
          />
        ))}
      </MuiTabs>
    </Box>
  );
}
