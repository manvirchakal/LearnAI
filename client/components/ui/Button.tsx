"use client";
import { Button as MuiButton, ButtonProps, CircularProgress } from "@mui/material";
import { forwardRef } from "react";

interface Props extends ButtonProps {
  loading?: boolean;
}

const Button = forwardRef<HTMLButtonElement, Props>(({ loading, disabled, children, ...props }, ref) => (
  <MuiButton ref={ref} disabled={disabled || loading} {...props}>
    {loading ? <CircularProgress size={16} color="inherit" sx={{ mr: children ? 1 : 0 }} /> : null}
    {children}
  </MuiButton>
));
Button.displayName = "Button";

export default Button;
