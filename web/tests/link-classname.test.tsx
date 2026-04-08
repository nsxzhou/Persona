import { render, screen } from "@testing-library/react";
import Link from "next/link";
import { Slot } from "@radix-ui/react-slot";

test("Slot passes className to Link", () => {
  render(
    <Slot className="my-test-class">
      <Link href="/test">Test</Link>
    </Slot>
  );
  expect(screen.getByText("Test")).toHaveClass("my-test-class");
});
