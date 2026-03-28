"use client";
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  IconButton, Typography, DialogProps,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { ReactNode } from "react";

interface Props extends Omit<DialogProps, "title"> {
  title?: ReactNode;
  actions?: ReactNode;
  onClose: () => void;
}

export default function Modal({ title, actions, onClose, children, ...props }: Props) {
  return (
    <Dialog onClose={onClose} {...props}>
      {title && (
        <DialogTitle sx={{ pr: 6 }}>
          <Typography variant="h6" component="span" fontWeight={600}>{title}</Typography>
          <IconButton onClick={onClose} sx={{ position: "absolute", right: 8, top: 8 }} size="small">
            <CloseIcon fontSize="small" />
          </IconButton>
        </DialogTitle>
      )}
      <DialogContent>{children}</DialogContent>
      {actions && <DialogActions sx={{ px: 3, pb: 2 }}>{actions}</DialogActions>}
    </Dialog>
  );
}
