import React, { useEffect } from "react";
import { Pagination, IconButton, ButtonGroup } from "@chakra-ui/react";
import { LuChevronLeft, LuChevronRight } from "react-icons/lu";

// explicitly 1-based to prevent +/-1-confusion errors
export const FIRST_PAGE = 1 as PaginationPage;
export const parsePaginationPage = (
  page: number,
):
  | {
      value: PaginationPage;
    }
  | {
      error: string;
    } => {
  if (page < FIRST_PAGE)
    return {
      error: "Page must be greater than 0",
    };
  if (!Number.isInteger(page))
    return {
      error: "Page must be an integer",
    };
  return {
    value: page as PaginationPage,
  };
};
export type PaginationPage = number & { __brand: "PaginationPage" };
export const PaginationPage = (page: number): PaginationPage => {
  const v = parsePaginationPage(page);
  if ("error" in v) throw new Error(v.error);
  return v.value;
};

export const paginationPageTo0Based = (page: PaginationPage): number =>
  page - FIRST_PAGE;

type PaginationProps = {
  page: PaginationPage;
  setPage: (page: PaginationPage) => void;
  total: number;
  size: number;
};

export const totalPages = (total: number, size: number) => {
  return Math.ceil(total / size);
};

export default function PaginationComponent(props: PaginationProps) {
  const { page, setPage, total, size } = props;
  useEffect(() => {
    if (page > totalPages(total, size)) {
      console.error(
        `Page number (${page}) is greater than total pages (${totalPages}) in pagination`,
      );
    }
  }, [page, totalPages(total, size)]);

  return (
    <Pagination.Root
      count={total}
      pageSize={size}
      page={page}
      onPageChange={(details) => setPage(PaginationPage(details.page))}
      style={{ display: "flex", justifyContent: "center" }}
    >
      <ButtonGroup variant="ghost" size="xs">
        <Pagination.PrevTrigger asChild>
          <IconButton>
            <LuChevronLeft />
          </IconButton>
        </Pagination.PrevTrigger>
        <Pagination.Items
          render={(page) => (
            <IconButton variant={{ base: "ghost", _selected: "solid" }}>
              {page.value}
            </IconButton>
          )}
        />
        <Pagination.NextTrigger asChild>
          <IconButton>
            <LuChevronRight />
          </IconButton>
        </Pagination.NextTrigger>
      </ButtonGroup>
    </Pagination.Root>
  );
}
