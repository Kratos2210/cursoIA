import type { MDXComponents } from "mdx/types";
import * as Content from "@/components/content/mdx";
import { Quiz, Question, Prompt, Option, Feedback } from "@/components/interactive/Quiz";

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
    ...components,
  };
}
