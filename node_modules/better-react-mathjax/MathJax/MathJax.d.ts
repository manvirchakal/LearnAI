import { ComponentPropsWithoutRef, FC } from "react";
import { MathJaxOverrideableProps } from "../MathJaxContext";
export interface MathJaxProps extends MathJaxOverrideableProps {
    inline?: boolean;
    onInitTypeset?: () => void;
    onTypeset?: () => void;
    text?: string;
    dynamic?: boolean;
}
declare const MathJax: FC<MathJaxProps & ComponentPropsWithoutRef<"span">>;
export default MathJax;
