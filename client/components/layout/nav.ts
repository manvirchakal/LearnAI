import {
  BookOpenIcon,
  FolderKanbanIcon,
  HouseIcon,
  PlayCircleIcon,
  UploadIcon,
  UserRoundIcon,
} from "lucide-react";

export const NAV = [
  { href: "/upload", label: "Upload", icon: UploadIcon },
  { href: "/library", label: "Library", icon: BookOpenIcon },
  { href: "/collections", label: "Collections", icon: FolderKanbanIcon },
  { href: "/media", label: "Media", icon: PlayCircleIcon },
  { href: "/questionnaire", label: "Profile", icon: UserRoundIcon },
];

/** Bottom tab bar on phones; Profile moves to the header there */
export const MOBILE_NAV = [
  { href: "/home", label: "Home", icon: HouseIcon },
  NAV[1],
  NAV[0],
  NAV[2],
  NAV[3],
];

export const isActivePath = (pathname: string, href: string) =>
  pathname === href || pathname.startsWith(`${href}/`) || (href === "/library" && pathname.startsWith("/study"));
