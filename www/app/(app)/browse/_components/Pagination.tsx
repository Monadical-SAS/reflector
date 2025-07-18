import React from "react";
import { Pagination, IconButton, ButtonGroup } from "@chakra-ui/react";
import { FaChevronLeft, FaChevronRight } from "react-icons/fa";

type PaginationProps = {
  page: number;
  setPage: (page: number) => void;
  total: number;
  size: number;
};

export default function PaginationComponent(props: PaginationProps) {
  const { page, setPage, total, size } = props;
  const totalPages = Math.ceil(total / size);

  if (totalPages <= 1) return null;

  return (
    <Pagination.Root
      count={total}
      pageSize={size}
      page={page}
      onPageChange={(details) => setPage(details.page)}
      style={{ display: "flex", justifyContent: "center" }}
    >
      <ButtonGroup variant="ghost" size="xs">
        <Pagination.PrevTrigger asChild>
          <IconButton>
            <FaChevronLeft />
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
            <FaChevronRight />
          </IconButton>
        </Pagination.NextTrigger>
      </ButtonGroup>
    </Pagination.Root>
  );
}
