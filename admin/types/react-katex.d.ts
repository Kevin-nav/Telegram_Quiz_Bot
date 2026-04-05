declare module "react-katex" {
  import type { ReactElement, ReactNode } from "react";

  export type RenderErrorCallback = (error: Error) => ReactNode;

  export interface MathComponentProps {
    children?: string;
    math?: string;
    errorColor?: string;
    renderError?: RenderErrorCallback;
  }

  export function InlineMath(props: MathComponentProps): ReactElement;
  export function BlockMath(props: MathComponentProps): ReactElement;
}
