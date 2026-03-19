import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./features/home/home.component').then(m => m.HomeComponent)
  },
  {
    path: 'editor',
    loadComponent: () => import('./features/editor/editor.component').then(m => m.EditorComponent)
  },
  {
    path: 'print/:id',
    loadComponent: () => import('./features/print/print.component').then(m => m.PrintComponent)
  },
  {
    path: '**',
    redirectTo: ''
  }
];

