import type { MDXComponents } from "mdx/types";
import * as Content from "@/components/content/mdx";
import { Quiz, Question, Prompt, Option, Feedback } from "@/components/interactive/Quiz";
import { CodeBlock } from "@/components/content/CodeBlock";
import { PlaygroundSoftmax } from "@/components/interactive/PlaygroundSoftmax";
import { PlaygroundRerank } from "@/components/interactive/PlaygroundRerank";
import { PlaygroundGrafo } from "@/components/interactive/PlaygroundGrafo";
import { PlaygroundChunks } from "@/components/interactive/PlaygroundChunks";

// Wires the course's custom MDX vocabulary (emitted by the HTML→MDX converter)
// into every .mdx file. Required at the project root by @next/mdx in the App Router.
export function useMDXComponents(components: MDXComponents): MDXComponents {
  return {
    ...Content,
    Quiz,
    Question,
    Prompt,
    Option,
    Feedback,
    PlaygroundSoftmax,
    PlaygroundRerank,
    PlaygroundGrafo,
    PlaygroundChunks,
    // Every shiki-highlighted <pre> gets a floating copy button (client). The
    // caption bar around it, when present, is added statically by rehype-code-title.
    pre: CodeBlock,
    ...components,
  };
}
