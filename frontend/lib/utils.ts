import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import katex from "katex";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatPercentage(value: number): string {
  return `${value.toFixed(2)}%`;
}

export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(date));
}

export function renderMath(text: string): string {
  return text.replace(/\$([^$]+)\$/g, (_, expr) =>
    katex.renderToString(expr, { throwOnError: false })
  );
}

export function formatLLMResponse(raw: string): string {
  let text = raw
    // Hapus tag pembuka/penutup <p>
    .replace(/^<p.*?>|<\/p>$/g, "")
    .trim();

  // Ganti dua newline dengan <br><br>
  text = text.replace(/\n{2,}/g, "<br><br>");

  // Markdown **bold**
  text = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

  // Markdown bullet list (- atau •)
  if (text.includes("- ") || text.includes("• ")) {
    text = text.replace(/(?:^|\n)[-•] (.*?)(?=\n|$)/g, "<li>$1</li>");
    text = text.replace(
      /(<li>.*<\/li>)/gs,
      '<ul class="list-disc pl-5">$1</ul>'
    );
  }

  // Markdown table → HTML table
  if (text.includes("|")) {
    text = text.replace(/((?:\|.*\|\n)+)/g, (match) => {
      const rows = match
        .trim()
        .split("\n")
        .map(
          (r) =>
            "<tr>" +
            r
              .trim()
              .split("|")
              .filter(Boolean)
              .map(
                (c) =>
                  `<td class="border border-gray-300 px-2 py-1">${c.trim()}</td>`
              )
              .join("") +
            "</tr>"
        );
      return `<table class="border-collapse border border-gray-400 text-sm my-2">${rows.join(
        ""
      )}</table>`;
    });
  }

  // Bersihkan escape LaTeX (\( ... \), \[ ... \])
  text = text.replace(/\\\(|\\\)/g, "");
  text = text.replace(/\\\[(.*?)\\\]/g, "<div class='my-2 font-mono'>$1</div>");

  // Ganti newline dengan <br>
  text = text.replace(/\n/g, "<br>");

  return `<div class="prose prose-sm leading-relaxed max-w-none">${text}</div>`;
}
