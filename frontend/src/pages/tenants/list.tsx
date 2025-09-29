import React from "react";
import {
  List,
  TextField,
  BooleanField,
  DateField,
  useTable,
  EditButton,
  ShowButton,
  DeleteButton,
} from "@refinedev/mui";
import { Table, TableBody, TableCell, TableHead, TableRow } from "@mui/material";

export const TenantList = () => {
  const { tableQueryResult } = useTable({
    resource: "tenants",
  });

  const { data, isLoading } = tableQueryResult;

  return (
    <List>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>ID</TableCell>
            <TableCell>Name</TableCell>
            <TableCell>Domain</TableCell>
            <TableCell>Active</TableCell>
            <TableCell>Created At</TableCell>
            <TableCell>Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {data?.data?.map((tenant) => (
            <TableRow key={tenant.id}>
              <TableCell>
                <TextField value={tenant.id} />
              </TableCell>
              <TableCell>
                <TextField value={tenant.name} />
              </TableCell>
              <TableCell>
                <TextField value={tenant.domain} />
              </TableCell>
              <TableCell>
                <BooleanField value={tenant.is_active} />
              </TableCell>
              <TableCell>
                <DateField value={tenant.created_at} />
              </TableCell>
              <TableCell>
                <EditButton hideText recordItemId={tenant.id} />
                <ShowButton hideText recordItemId={tenant.id} />
                <DeleteButton hideText recordItemId={tenant.id} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </List>
  );
};