'use client';

import React, { useEffect, useState } from 'react';
import { useWorkflowStore } from '@/stores/workflowStore';
import { api } from '@/services/api';
import { RefreshCw, Plus, Edit2, Trash2, X, PlusCircle, Check } from 'lucide-react';

export default function CatalogPage() {
  const { businessId } = useWorkflowStore();
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Form State
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [price, setPrice] = useState('');
  const [category, setCategory] = useState('default');
  const [description, setDescription] = useState('');
  const [imageUrl, setImageUrl] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const fetchCatalog = async () => {
    if (!businessId) return;
    try {
      const res = await api.getCatalog(businessId);
      if (res.success && res.data) {
        setItems(res.data || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCatalog();
  }, [businessId]);

  const resetForm = () => {
    setEditingId(null);
    setName('');
    setPrice('');
    setCategory('default');
    setDescription('');
    setImageUrl('');
    setIsFormOpen(false);
  };

  const handleEditClick = (item: any) => {
    setEditingId(item.id || item.item_id);
    setName(item.name || '');
    setPrice(String(item.price || ''));
    setCategory(item.category || 'default');
    setDescription(item.description || '');
    setImageUrl(item.image_url || '');
    setIsFormOpen(true);
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessId || !name || !price) return;
    setSubmitting(true);

    const numPrice = parseFloat(price);
    const itemData = {
      name,
      price: numPrice,
      category,
      description,
      image_url: imageUrl
    };

    try {
      let res;
      if (editingId) {
        res = await api.updateCatalogItem(businessId, editingId, itemData);
      } else {
        res = await api.createCatalogItem(businessId, itemData);
      }

      if (res.success) {
        await fetchCatalog();
        resetForm();
      } else {
        alert('Failed to save item: ' + (res.error?.message || 'Unknown error'));
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteClick = async (itemId: string) => {
    if (!businessId) return;
    if (!confirm('Are you sure you want to delete this catalog item?')) return;

    try {
      const res = await api.deleteCatalogItem(businessId, itemId);
      if (res.success) {
        await fetchCatalog();
      } else {
        alert('Failed to delete item: ' + (res.error?.message || 'Unknown error'));
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="flex-1 p-8 flex flex-col gap-6 bg-slate-50/50">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="font-outfit font-bold text-xl text-slate-900">Catalog Manager</h2>
          <p className="text-xs text-slate-500 mt-1">Configure products, service pricing, and description categories for automated chatbot traversal.</p>
        </div>
        <div className="flex gap-2">
          <button 
            onClick={fetchCatalog}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 cursor-pointer shadow-sm transition-all"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
          <button 
            onClick={() => setIsFormOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-650 hover:bg-emerald-500 text-xs font-bold text-white shadow-sm transition-all cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" /> Add Product
          </button>
        </div>
      </div>

      {isFormOpen && (
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col gap-4 max-w-xl">
          <div className="flex justify-between items-center border-b border-slate-100 pb-3">
            <h3 className="font-extrabold text-sm text-slate-800">{editingId ? 'Edit Product' : 'Add New Product'}</h3>
            <button onClick={resetForm} className="text-slate-400 hover:text-slate-600 cursor-pointer">
              <X className="w-4 h-4" />
            </button>
          </div>

          <form onSubmit={handleFormSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="flex flex-col gap-1.5">
              <label className="font-semibold text-slate-600">Product Name *</label>
              <input 
                type="text" 
                value={name} 
                onChange={(e) => setName(e.target.value)} 
                required
                className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                placeholder="e.g. Margherita Pizza"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="font-semibold text-slate-600">Price ($) *</label>
              <input 
                type="number" 
                step="0.01"
                value={price} 
                onChange={(e) => setPrice(e.target.value)} 
                required
                className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                placeholder="e.g. 12.00"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="font-semibold text-slate-600">Category</label>
              <input 
                type="text" 
                value={category} 
                onChange={(e) => setCategory(e.target.value)} 
                className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                placeholder="e.g. Mains, Sides"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="font-semibold text-slate-600">Image URL</label>
              <input 
                type="text" 
                value={imageUrl} 
                onChange={(e) => setImageUrl(e.target.value)} 
                className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors"
                placeholder="e.g. https://image.url/pizza.jpg"
              />
            </div>

            <div className="flex flex-col gap-1.5 md:col-span-2">
              <label className="font-semibold text-slate-600">Description</label>
              <textarea 
                value={description} 
                onChange={(e) => setDescription(e.target.value)} 
                className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-colors h-20"
                placeholder="Brief catalog description..."
              />
            </div>

            <div className="flex justify-end gap-2 md:col-span-2 border-t border-slate-100 pt-4">
              <button 
                type="button" 
                onClick={resetForm}
                className="px-3 py-1.5 border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50 cursor-pointer font-semibold"
              >
                Cancel
              </button>
              <button 
                type="submit" 
                disabled={submitting}
                className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-bold flex items-center gap-1.5 cursor-pointer shadow-sm"
              >
                {submitting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                {editingId ? 'Update Product' : 'Create Product'}
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-slate-400">
          <RefreshCw className="w-6 h-6 text-emerald-600 animate-spin" />
        </div>
      ) : items.length > 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-500 uppercase tracking-wider">
                <th className="p-4">Item ID</th>
                <th className="p-4">Name</th>
                <th className="p-4">Category</th>
                <th className="p-4">Price</th>
                <th className="p-4">Description</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
              {items.map((item) => {
                const itemId = item.id || item.item_id;
                return (
                  <tr key={itemId} className="hover:bg-slate-50/50 transition-colors">
                    <td className="p-4 font-mono text-[10px] text-slate-400">{itemId}</td>
                    <td className="p-4 font-extrabold text-slate-800">{item.name}</td>
                    <td className="p-4">
                      <span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded text-[10px] font-bold uppercase font-mono">
                        {item.category || 'default'}
                      </span>
                    </td>
                    <td className="p-4 font-bold text-slate-900">${parseFloat(item.price || 0).toFixed(2)}</td>
                    <td className="p-4 text-slate-500 max-w-xs truncate" title={item.description}>{item.description || '—'}</td>
                    <td className="p-4 text-right">
                      <div className="flex gap-2 justify-end">
                        <button 
                          onClick={() => handleEditClick(item)}
                          className="p-1 rounded hover:bg-slate-100 text-slate-500 hover:text-slate-800 transition-colors cursor-pointer"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button 
                          onClick={() => handleDeleteClick(itemId)}
                          className="p-1 rounded hover:bg-rose-50 text-slate-500 hover:text-rose-600 transition-colors cursor-pointer"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="p-12 text-center text-xs text-slate-400 font-semibold border border-dashed border-slate-200 rounded-xl bg-white shadow-sm flex flex-col items-center gap-2">
          <PlusCircle className="w-8 h-8 text-slate-300" />
          No catalog products registered. Create one to populate your chatbot catalog.
        </div>
      )}
    </div>
  );
}
