import React from "react";
import {
  List,
  TextField,
  useTable,
  EditButton,
  ShowButton,
  DeleteButton,
} from "@refinedev/mui";
import { Table, TableBody, TableCell, TableHead, TableRow } from "@mui/material";

export const RoleList = () => {
  const { tableQueryResult } = useTable({
    resource: "roles",
  });

  const { data, isLoading } = tableQueryResult;

  return (
    <List>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>ID</TableCell>
            <TableCell>Name</TableCell>
            <TableCell>Description</TableCell>
            <TableCell>Client ID</TableCell>
            <TableCell>Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {data?.data?.map((role) => (
            <TableRow key={role.id}>
              <TableCell>
                <TextField value={role.id} />
              </TableCell>
              <TableCell>
                <TextField value={role.name} />
              </TableCell>
              <TableCell>
                <TextField value={role.description} />
              </TableCell>
              <TableCell>
                <TextField value={role.client_id} />
              </TableCell>
              <TableCell>
                <EditButton hideText recordItemId={role.id} />
                <ShowButton hideText recordItemId={role.id} />
                <DeleteButton hideText recordItemId={role.id} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </List>
  );
};